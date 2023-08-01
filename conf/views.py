import hashlib
import json
import os
import re
import shutil
import smtplib
import time
from datetime import datetime

import pytz
import requests
from django.conf import settings
from django.utils import timezone
from requests.exceptions import RequestException

from account.decorators import super_admin_required
from account.models import User
from contest.models import Contest
from judge.dispatcher import process_pending_task
from options.options import SysOptions
from problem.models import Problem
from submission.models import Submission
from utils.api import APIView, CSRFExemptAPIView, validate_serializer
from utils.shortcuts import send_email, get_env
from utils.xss_filter import XSSHtml
from .models import JudgeServer
from .serializers import (CreateEditWebsiteConfigSerializer,
                          CreateSMTPConfigSerializer, EditSMTPConfigSerializer,
                          JudgeServerHeartbeatSerializer,
                          JudgeServerSerializer, TestSMTPConfigSerializer, EditJudgeServerSerializer)


class SMTPAPI(APIView):
    @super_admin_required
    def get(self, request):
        smtp = SysOptions.smtp_config
        if not smtp:
            return self.success(None)
        smtp.pop("password")
        return self.success(smtp)

    @super_admin_required
    @validate_serializer(CreateSMTPConfigSerializer)
    def post(self, request):
        SysOptions.smtp_config = request.data
        return self.success()

    @super_admin_required
    @validate_serializer(EditSMTPConfigSerializer)
    def put(self, request):
        smtp = SysOptions.smtp_config
        data = request.data
        for item in ["server", "port", "email", "tls"]:
            smtp[item] = data[item]
        if "password" in data:
            smtp["password"] = data["password"]
        SysOptions.smtp_config = smtp
        return self.success()


class SMTPTestAPI(APIView):
    @super_admin_required
    @validate_serializer(TestSMTPConfigSerializer)
    def post(self, request):
        if not SysOptions.smtp_config:
            return self.error("Please setup SMTP config at first")
        try:
            send_email(smtp_config=SysOptions.smtp_config,
                       from_name=SysOptions.website_name_shortcut,
                       to_name=request.user.username,
                       to_email=request.data["email"],
                       subject="You have successfully configured SMTP",
                       content="You have successfully configured SMTP")
        except smtplib.SMTPResponseException as e:
            # guess error message encoding
            msg = b"Failed to send email"
            try:
                msg = e.smtp_error
                # qq mail
                msg = msg.decode("gbk")
            except Exception:
                msg = msg.decode("utf-8", "ignore")
            return self.error(msg)
        except Exception as e:
            msg = str(e)
            return self.error(msg)
        return self.success()


class WebsiteConfigAPI(APIView):
    def get(self, request):
        ret = {key: getattr(SysOptions, key) for key in
               ["website_base_url", "website_name", "website_name_shortcut",
                "website_footer", "allow_register", "submission_list_show_all"]}
        return self.success(ret)

    @super_admin_required
    @validate_serializer(CreateEditWebsiteConfigSerializer)
    def post(self, request):
        for k, v in request.data.items():
            if k == "website_footer":
                with XSSHtml() as parser:
                    v = parser.clean(v)
            setattr(SysOptions, k, v)
        return self.success()


class JudgeServerAPI(APIView):
    @super_admin_required
    def get(self, request):
        servers = JudgeServer.objects.all().order_by("-last_heartbeat")
        return self.success({"token": SysOptions.judge_server_token,
                             "servers": JudgeServerSerializer(servers, many=True).data})

    @super_admin_required
    def delete(self, request):
        hostname = request.GET.get("hostname")
        if hostname:
            JudgeServer.objects.filter(hostname=hostname).delete()
        return self.success()

    @validate_serializer(EditJudgeServerSerializer)
    @super_admin_required
    def put(self, request):
        is_disabled = request.data.get("is_disabled", False)
        JudgeServer.objects.filter(id=request.data["id"]).update(is_disabled=is_disabled)
        if not is_disabled:
            process_pending_task()
        return self.success()


class JudgeServerHeartbeatAPI(CSRFExemptAPIView):
    @validate_serializer(JudgeServerHeartbeatSerializer)
    def post(self, request):
        data = request.data
        client_token = request.META.get("HTTP_X_JUDGE_SERVER_TOKEN")
        if hashlib.sha256(SysOptions.judge_server_token.encode("utf-8")).hexdigest() != client_token:
            return self.error("Invalid token")

        try:
            server = JudgeServer.objects.get(hostname=data["hostname"])
            server.judger_version = data["judger_version"]
            server.cpu_core = data["cpu_core"]
            server.memory_usage = data["memory"]
            server.cpu_usage = data["cpu"]
            server.service_url = data["service_url"]
            server.ip = request.ip
            server.last_heartbeat = timezone.now()
            server.save(update_fields=["judger_version", "cpu_core", "memory_usage", "service_url", "ip", "last_heartbeat"])
        except JudgeServer.DoesNotExist:
            JudgeServer.objects.create(hostname=data["hostname"],
                                       judger_version=data["judger_version"],
                                       cpu_core=data["cpu_core"],
                                       memory_usage=data["memory"],
                                       cpu_usage=data["cpu"],
                                       ip=request.META["REMOTE_ADDR"],
                                       service_url=data["service_url"],
                                       last_heartbeat=timezone.now(),
                                       )
        # 新server上线 处理队列中的，防止没有新的提交而导致一直waiting
        process_pending_task()

        return self.success()


class LanguagesAPI(APIView):
    data = {
        "languages": [
            {
                "spj": {
                    "config": {
                        "command": "{exe_path} {in_file_path} {user_out_file_path}",
                        "exe_name": "spj-{spj_version}",
                        "seccomp_rule": "c_cpp"
                    },
                    "compile": {
                        "exe_name": "spj-{spj_version}",
                        "src_name": "spj-{spj_version}.c",
                        "max_memory": 1073741824,
                        "max_cpu_time": 3000,
                        "max_real_time": 10000,
                        "compile_command": "/usr/bin/gcc -DONLINE_JUDGE -O2 -w -fmax-errors=3 -std=c11 {src_path} -lm -o {exe_path}"
                    }
                },
                "name": "C",
                "config": {
                    "run": {
                        "env": [
                            "LANG=en_US.UTF-8",
                            "LANGUAGE=en_US:en",
                            "LC_ALL=en_US.UTF-8"
                        ],
                        "command": "{exe_path}",
                        "seccomp_rule": {
                            "File IO": "c_cpp_file_io",
                            "Standard IO": "c_cpp"
                        }
                    },
                    "compile": {
                        "exe_name": "main",
                        "src_name": "main.c",
                        "max_memory": 268435456,
                        "max_cpu_time": 3000,
                        "max_real_time": 10000,
                        "compile_command": "/usr/bin/gcc -DONLINE_JUDGE -O2 -w -fmax-errors=3 -std=c11 {src_path} -lm -o {exe_path}"
                    },
                    "template": "//PREPEND BEGIN\n#include <stdio.h>\n//PREPEND END\n\n//TEMPLATE BEGIN\nint add(int a, int b) {\n  // Please fill this blank\n  return ___________;\n}\n//TEMPLATE END\n\n//APPEND BEGIN\nint main() {\n  printf(\"%d\", add(1, 2));\n  return 0;\n}\n//APPEND END"
                },
                "description": "GCC 9.4",
                "content_type": "text/x-csrc"
            },
            {
                "spj": {
                    "config": {
                        "command": "{exe_path} {in_file_path} {user_out_file_path}",
                        "exe_name": "spj-{spj_version}",
                        "seccomp_rule": "c_cpp"
                    },
                    "compile": {
                        "exe_name": "spj-{spj_version}",
                        "src_name": "spj-{spj_version}.cpp",
                        "max_memory": 1073741824,
                        "max_cpu_time": 10000,
                        "max_real_time": 20000,
                        "compile_command": "/usr/bin/g++ -DONLINE_JUDGE -O2 -w -fmax-errors=3 -std=c++14 {src_path} -lm -o {exe_path}"
                    }
                },
                "name": "C++",
                "config": {
                    "run": {
                        "env": [
                            "LANG=en_US.UTF-8",
                            "LANGUAGE=en_US:en",
                            "LC_ALL=en_US.UTF-8"
                        ],
                        "command": "{exe_path}",
                        "seccomp_rule": {
                            "File IO": "c_cpp_file_io",
                            "Standard IO": "c_cpp"
                        }
                    },
                    "compile": {
                        "exe_name": "main",
                        "src_name": "main.cpp",
                        "max_memory": 1073741824,
                        "max_cpu_time": 10000,
                        "max_real_time": 20000,
                        "compile_command": "/usr/bin/g++ -DONLINE_JUDGE -O2 -w -fmax-errors=3 -std=c++14 {src_path} -lm -o {exe_path}"
                    },
                    "template": "//PREPEND BEGIN\n#include <iostream>\n//PREPEND END\n\n//TEMPLATE BEGIN\nint add(int a, int b) {\n  // Please fill this blank\n  return ___________;\n}\n//TEMPLATE END\n\n//APPEND BEGIN\nint main() {\n  std::cout << add(1, 2);\n  return 0;\n}\n//APPEND END"
                },
                "description": "G++ 14",
                "content_type": "text/x-c++src"
            },
            {
                "name": "Java",
                "config": {
                    "run": {
                        "env": [
                            "LANG=en_US.UTF-8",
                            "LANGUAGE=en_US:en",
                            "LC_ALL=en_US.UTF-8"
                        ],
                        "command": "/usr/bin/java -cp {exe_dir} -XX:MaxRAM={max_memory}k -Djava.security.manager -Dfile.encoding=UTF-8 -Djava.security.policy==/etc/java_policy -Djava.awt.headless=true Main",
                        "seccomp_rule": None,
                        "memory_limit_check_only": 1
                    },
                    "compile": {
                        "exe_name": "Main",
                        "src_name": "Main.java",
                        "max_memory": -1,
                        "max_cpu_time": 5000,
                        "max_real_time": 10000,
                        "compile_command": "/usr/bin/javac {src_path} -d {exe_dir} -encoding UTF8"
                    },
                    "template": "//PREPEND BEGIN\n//PREPEND END\n\n//TEMPLATE BEGIN\n//TEMPLATE END\n\n//APPEND BEGIN\n//APPEND END"
                },
                "description": "OpenJDK 11",
                "content_type": "text/x-java"
            },
            {
                "name": "Python2",
                "config": {
                    "run": {
                        "env": [
                            "LANG=en_US.UTF-8",
                            "LANGUAGE=en_US:en",
                            "LC_ALL=en_US.UTF-8"
                        ],
                        "command": "/usr/bin/python {exe_path}",
                        "seccomp_rule": "general"
                    },
                    "compile": {
                        "exe_name": "solution.pyc",
                        "src_name": "solution.py",
                        "max_memory": 134217728,
                        "max_cpu_time": 3000,
                        "max_real_time": 10000,
                        "compile_command": "/usr/bin/python -m py_compile {src_path}"
                    },
                    "template": "//PREPEND BEGIN\n//PREPEND END\n\n//TEMPLATE BEGIN\n//TEMPLATE END\n\n//APPEND BEGIN\n//APPEND END"
                },
                "description": "Python 2.7",
                "content_type": "text/x-python"
            },
            {
                "name": "Python3",
                "config": {
                    "run": {
                        "env": [
                            "LANG=en_US.UTF-8",
                            "LANGUAGE=en_US:en",
                            "LC_ALL=en_US.UTF-8",
                            "PYTHONIOENCODING=utf-8"
                        ],
                        "command": "/usr/bin/python3 {exe_path}",
                        "seccomp_rule": "general"
                    },
                    "compile": {
                        "exe_name": "__pycache__/solution.cpython-36.pyc",
                        "src_name": "solution.py",
                        "max_memory": 134217728,
                        "max_cpu_time": 3000,
                        "max_real_time": 10000,
                        "compile_command": "/usr/bin/python3 -m py_compile {src_path}"
                    },
                    "template": "//PREPEND BEGIN\n//PREPEND END\n\n//TEMPLATE BEGIN\n//TEMPLATE END\n\n//APPEND BEGIN\n//APPEND END"
                },
                "description": "Python 3",
                "content_type": "text/x-python"
            },
            {
                "name": "Golang",
                "config": {
                    "run": {
                        "env": [
                            "GODEBUG=madvdontneed=1",
                            "GOMAXPROCS=1",
                            "LANG=en_US.UTF-8",
                            "LANGUAGE=en_US:en",
                            "LC_ALL=en_US.UTF-8"
                        ],
                        "command": "{exe_path}",
                        "seccomp_rule": "golang",
                        "memory_limit_check_only": 1
                    },
                    "compile": {
                        "env": [
                            "GOCACHE=/tmp",
                            "GOPATH=/tmp",
                            "GOMAXPROCS=1",
                            "LANG=en_US.UTF-8",
                            "LANGUAGE=en_US:en",
                            "LC_ALL=en_US.UTF-8"
                        ],
                        "exe_name": "main",
                        "src_name": "main.go",
                        "max_memory": 1073741824,
                        "max_cpu_time": 3000,
                        "max_real_time": 5000,
                        "compile_command": "/usr/bin/go build -o {exe_path} {src_path}"
                    },
                    "template": "//PREPEND BEGIN\n//PREPEND END\n\n//TEMPLATE BEGIN\n//TEMPLATE END\n\n//APPEND BEGIN\n//APPEND END"
                },
                "description": "Golang 1.17",
                "content_type": "text/x-go"
            },
            {
                "name": "JavaScript",
                "config": {
                    "run": {
                        "env": [
                            "LANG=en_US.UTF-8",
                            "LANGUAGE=en_US:en",
                            "LC_ALL=en_US.UTF-8"
                        ],
                        "command": "/usr/bin/node {exe_path}",
                        "seccomp_rule": "node",
                        "memory_limit_check_only": 1
                    },
                    "compile": {
                        "env": [
                            "LANG=en_US.UTF-8",
                            "LANGUAGE=en_US:en",
                            "LC_ALL=en_US.UTF-8"
                        ],
                        "exe_name": "main.js",
                        "src_name": "main.js",
                        "max_memory": 1073741824,
                        "max_cpu_time": 3000,
                        "max_real_time": 5000,
                        "compile_command": "/usr/bin/node --check {src_path}"
                    },
                    "template": "//PREPEND BEGIN\n//PREPEND END\n\n//TEMPLATE BEGIN\n//TEMPLATE END\n\n//APPEND BEGIN\n//APPEND END"
                },
                "description": "Node 14",
                "content_type": "text/javascript"
            }
        ],
        "spj_languages": [
            {
                "spj": {
                    "config": {
                        "command": "{exe_path} {in_file_path} {user_out_file_path}",
                        "exe_name": "spj-{spj_version}",
                        "seccomp_rule": "c_cpp"
                    },
                    "compile": {
                        "exe_name": "spj-{spj_version}",
                        "src_name": "spj-{spj_version}.c",
                        "max_memory": 1073741824,
                        "max_cpu_time": 3000,
                        "max_real_time": 10000,
                        "compile_command": "/usr/bin/gcc -DONLINE_JUDGE -O2 -w -fmax-errors=3 -std=c11 {src_path} -lm -o {exe_path}"
                    }
                },
                "name": "C",
                "config": {
                    "run": {
                        "env": [
                            "LANG=en_US.UTF-8",
                            "LANGUAGE=en_US:en",
                            "LC_ALL=en_US.UTF-8"
                        ],
                        "command": "{exe_path}",
                        "seccomp_rule": {
                            "File IO": "c_cpp_file_io",
                            "Standard IO": "c_cpp"
                        }
                    },
                    "compile": {
                        "exe_name": "main",
                        "src_name": "main.c",
                        "max_memory": 268435456,
                        "max_cpu_time": 3000,
                        "max_real_time": 10000,
                        "compile_command": "/usr/bin/gcc -DONLINE_JUDGE -O2 -w -fmax-errors=3 -std=c11 {src_path} -lm -o {exe_path}"
                    },
                    "template": "//PREPEND BEGIN\n#include <stdio.h>\n//PREPEND END\n\n//TEMPLATE BEGIN\nint add(int a, int b) {\n  // Please fill this blank\n  return ___________;\n}\n//TEMPLATE END\n\n//APPEND BEGIN\nint main() {\n  printf(\"%d\", add(1, 2));\n  return 0;\n}\n//APPEND END"
                },
                "description": "GCC 9.4",
                "content_type": "text/x-csrc"
            },
            {
                "spj": {
                    "config": {
                        "command": "{exe_path} {in_file_path} {user_out_file_path}",
                        "exe_name": "spj-{spj_version}",
                        "seccomp_rule": "c_cpp"
                    },
                    "compile": {
                        "exe_name": "spj-{spj_version}",
                        "src_name": "spj-{spj_version}.cpp",
                        "max_memory": 1073741824,
                        "max_cpu_time": 10000,
                        "max_real_time": 20000,
                        "compile_command": "/usr/bin/g++ -DONLINE_JUDGE -O2 -w -fmax-errors=3 -std=c++14 {src_path} -lm -o {exe_path}"
                    }
                },
                "name": "C++",
                "config": {
                    "run": {
                        "env": [
                            "LANG=en_US.UTF-8",
                            "LANGUAGE=en_US:en",
                            "LC_ALL=en_US.UTF-8"
                        ],
                        "command": "{exe_path}",
                        "seccomp_rule": {
                            "File IO": "c_cpp_file_io",
                            "Standard IO": "c_cpp"
                        }
                    },
                    "compile": {
                        "exe_name": "main",
                        "src_name": "main.cpp",
                        "max_memory": 1073741824,
                        "max_cpu_time": 10000,
                        "max_real_time": 20000,
                        "compile_command": "/usr/bin/g++ -DONLINE_JUDGE -O2 -w -fmax-errors=3 -std=c++14 {src_path} -lm -o {exe_path}"
                    },
                    "template": "//PREPEND BEGIN\n#include <iostream>\n//PREPEND END\n\n//TEMPLATE BEGIN\nint add(int a, int b) {\n  // Please fill this blank\n  return ___________;\n}\n//TEMPLATE END\n\n//APPEND BEGIN\nint main() {\n  std::cout << add(1, 2);\n  return 0;\n}\n//APPEND END"
                },
                "description": "G++ 14",
                "content_type": "text/x-c++src"
            }
        ]
    }
    def get(self, request):
        # return self.success({"languages": SysOptions.languages, "spj_languages": SysOptions.spj_languages})
        return self.success(self.data)


class TestCasePruneAPI(APIView):
    @super_admin_required
    def get(self, request):
        """
        return orphan test_case list
        """
        ret_data = []
        dir_to_be_removed = self.get_orphan_ids()

        # return an iterator
        for d in os.scandir(settings.TEST_CASE_DIR):
            if d.name in dir_to_be_removed:
                ret_data.append({"id": d.name, "create_time": d.stat().st_mtime})
        return self.success(ret_data)

    @super_admin_required
    def delete(self, request):
        test_case_id = request.GET.get("id")
        if test_case_id:
            self.delete_one(test_case_id)
            return self.success()
        for id in self.get_orphan_ids():
            self.delete_one(id)
        return self.success()

    @staticmethod
    def get_orphan_ids():
        db_ids = Problem.objects.all().values_list("test_case_id", flat=True)
        disk_ids = os.listdir(settings.TEST_CASE_DIR)
        test_case_re = re.compile(r"^[a-zA-Z0-9]{32}$")
        disk_ids = filter(lambda f: test_case_re.match(f), disk_ids)
        return list(set(disk_ids) - set(db_ids))

    @staticmethod
    def delete_one(id):
        test_case_dir = os.path.join(settings.TEST_CASE_DIR, id)
        if os.path.isdir(test_case_dir):
            shutil.rmtree(test_case_dir, ignore_errors=True)


class ReleaseNotesAPI(APIView):
    def get(self, request):
        try:
            resp = requests.get("https://raw.githubusercontent.com/QingdaoU/OnlineJudge/master/docs/data.json?_=" + str(time.time()),
                                timeout=3)
            releases = resp.json()
        except (RequestException, ValueError):
            return self.success()
        with open("docs/data.json", "r") as f:
            local_version = json.load(f)["update"][0]["version"]
        releases["local_version"] = local_version
        return self.success(releases)


class DashboardInfoAPI(APIView):
    def get(self, request):
        today = datetime.today()
        today_submission_count = Submission.objects.filter(
            create_time__gte=datetime(today.year, today.month, today.day, 0, 0, tzinfo=pytz.UTC)).count()
        recent_contest_count = Contest.objects.exclude(end_time__lt=timezone.now()).count()
        judge_server_count = len(list(filter(lambda x: x.status == "normal", JudgeServer.objects.all())))
        return self.success({
            "user_count": User.objects.count(),
            "recent_contest_count": recent_contest_count,
            "today_submission_count": today_submission_count,
            "judge_server_count": judge_server_count,
            "env": {
                "FORCE_HTTPS": get_env("FORCE_HTTPS", default=False),
                "STATIC_CDN_HOST": get_env("STATIC_CDN_HOST", default="")
            }
        })
