from django.contrib.auth.models import AbstractBaseUser
from django.conf import settings
from django.db import models
from utils.models import JSONField
from django.db.models import IntegerField
from django.db.models.functions import Cast
import logging


class AdminType(object):
    REGULAR_USER = "Regular User"
    ADMIN = "Admin"
    SUPER_ADMIN = "Super Admin"


class ProblemPermission(object):
    NONE = "None"
    OWN = "Own"
    ALL = "All"


class UserManager(models.Manager):
    use_in_migrations = True

    def get_by_natural_key(self, username):
        return self.get(**{f"{self.model.USERNAME_FIELD}__iexact": username})


class User(AbstractBaseUser):
    username = models.TextField(unique=True)
    email = models.TextField(null=True)
    create_time = models.DateTimeField(auto_now_add=True, null=True)
    # One of UserType
    admin_type = models.TextField(default=AdminType.REGULAR_USER)
    problem_permission = models.TextField(default=ProblemPermission.NONE)
    reset_password_token = models.TextField(null=True)
    reset_password_token_expire_time = models.DateTimeField(null=True)
    # SSO auth token
    auth_token = models.TextField(null=True)
    two_factor_auth = models.BooleanField(default=False)
    tfa_token = models.TextField(null=True)
    session_keys = JSONField(default=list)
    # open api key
    open_api = models.BooleanField(default=False)
    open_api_appkey = models.TextField(null=True)
    is_disabled = models.BooleanField(default=False)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def is_admin(self):
        return self.admin_type == AdminType.ADMIN or self.admin_type == AdminType.SUPER_ADMIN

    def is_super_admin(self):
        return self.admin_type == AdminType.SUPER_ADMIN

    def is_admin_role(self):
        return self.admin_type in [AdminType.ADMIN, AdminType.SUPER_ADMIN]

    def can_mgmt_all_problem(self):
        return self.problem_permission == ProblemPermission.ALL

    def is_contest_admin(self, contest):
        return self.is_authenticated and (contest.created_by == self or self.admin_type == AdminType.SUPER_ADMIN)

    class Meta:
        db_table = "user"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # acm_problems_status examples:
    # {
    #     "problems": {
    #         "1": {
    #             "status": JudgeStatus.ACCEPTED,
    #             "_id": "1000"
    #         }
    #     },
    #     "contest_problems": {
    #         "1": {
    #             "status": JudgeStatus.ACCEPTED,
    #             "_id": "1000"
    #         }
    #     }
    # }
    acm_problems_status = JSONField(default=dict)
    # like acm_problems_status, merely add "score" field
    oi_problems_status = JSONField(default=dict)

    real_name = models.TextField(null=True)
    avatar = models.TextField(default=f"{settings.AVATAR_URI_PREFIX}/default.png")
    blog = models.URLField(null=True)
    mood = models.TextField(null=True)
    github = models.TextField(null=True)
    school = models.TextField(null=True)
    major = models.TextField(null=True)
    language = models.TextField(null=True)
    # for ACM
    accepted_number = models.IntegerField(default=0)
    # for OI
    total_score = models.BigIntegerField(default=0)
    submission_number = models.IntegerField(default=0)

    defaultRL = {
        AdminType.ADMIN: [15000, 1], 
        AdminType.SUPER_ADMIN: [20000, 2], 
        AdminType.REGULAR_USER: [1000, 0]
    }

    colorSpan = [
        [
            [0, '<span style="color:pink;">{}</span>'],
            [1000, '<span style="color:green;">{}</span>'],
            [2000, '<span style="color:brown;">{}</span>'],
            [3000, '<span style="color:cyan;">{}</span>'],
            [4000, '<span style="color:bule;">{}</span>'],
            [5000, '<span style="color:purple;">{}</span>'],
            [8000, '<span style="color:red;">{}</span>'],
            [9999, '<span style="color:black;">{}<span style="color:red;">{}</span></span>'],
            [10001, '<span style="background-image: -webkit-linear-gradient(45deg, black, red);-webkit-background-clip: text;-webkit-text-fill-color: transparent;">{}</span>'],
        ],
        [
            [15001, '<span style="background-image: -webkit-linear-gradient(45deg, black, #FFDF00);-webkit-background-clip: text;-webkit-text-fill-color: transparent;">{}</span>'],
        ],
        [
            [20001, '<span style="background-image: -webkit-linear-gradient(45deg, red, #FFDF00);-webkit-background-clip: text;-webkit-text-fill-color: transparent;">{}</span>']
        ]
    ]

    userSpan = models.TextField(default="")

    RL_score = models.IntegerField(default=1000)
    ls_sc = models.IntegerField(default=1000)

    # RL_get example: {
    #   get_by_problem: {
    #       "1": {
    #           "score": 10
    #       }
    #   },
    #   get_by_contest: {
    #       "1": {
    #           "score": 10
    #       }
    #   }
    # }
    RL_get = JSONField(default=dict)

    padds = [
        [35, 60, 100], 
        [24, 35, 55], 
        [12, 45, 65],
        [8, 55, 80],
        [4, 60, 100],
        [1, 80, 200],
        [0, 100, 500],
        [500, 800, 1000]
    ]

    radds = [
        [[500, 0, 0, 1], [250, 0, 0, 1], [100, 0, 0, -1]],
        [[11, 106, 1, 1], [100, 0, 0, 1], [11, 66, 1, -1]],
        [[11, 96, 1, 1], [80, 0, 0, 1], [12, 56, 1, -1]],
        [[11, 76, 1, 1], [60, 0, 0, 1], [13, 61, 1, -1]],
        [[11, 62, 1, 1], [40, 0, 0, 1], [21, 81, 1, -1]],
        [[11, 48, 1, 1], [30, 0, 0, 1], [31, 101, 1, -1]],
        [[11, 156, 1, 1], [80, 0, 0, 1], [51, 201, 1, -1]],
        [[1000, 0, 0, 1], [500, 0, 0, 1], [1500, 0, 0, -1]],
    ]

    pdf2id = {
        "Low": 0,
        "Mid": 1,
        "High": 2
    } 

    def __init__(self, *args, **kwargs):
        super(UserProfile, self).__init__(*args, **kwargs)
        if self.user: 
            if self.user.admin_type == AdminType.REGULAR_USER:
                self.initMeta()
                idx = 0
                while self.RL_score >= self.colorSpan[0][idx][0]:
                    idx += 1
                if idx != 0: idx -= 1
                if idx == 7:
                    if len(self.user.username) > 1:
                        self.userSpan = self.colorSpan[0][idx][1].format(self.user.username[0], self.user.username[1:])
                    else:
                        self.userSpan = self.colorSpan[0][idx][1].format(self.user.username, self.user.username)
                else:
                    self.userSpan = self.colorSpan[0][idx][1].format(self.user.username)
            elif self.user.admin_type == AdminType.ADMIN:
                self.userSpan = self.colorSpan[1][0][1].format(self.user.username)
                self.RL_score = 15000
            else:
                self.userSpan = self.colorSpan[2][0][1].format(self.user.username)
                self.RL_score = 20000

    def initMeta(self):
        if self.user:
            self.RL_score = self.ls_sc

        self.save()

    def add_RL_score(self, pdiff=None, ranks=None):
        if self.user.admin_type != AdminType.REGULAR_USER: return
        score = self.RL_score
        fid = max(min((score + 1000) // 1000, 7), 0)
        if not pdiff is None:
            sid, problem_id = self.pdf2id[pdiff[0]], pdiff[1]
            score += self.padds[fid][sid]
            self.RL_get.setdefault("get_by_problem", {}).setdefault(problem_id, {})
            self.RL_get["get_by_problem"][problem_id]["score"] = self.padds[fid][sid]
        elif not ranks is None:
            sid, psr, contest_id = ranks
            x1, x2, x3, f1 = self.radds[fid][sid]
            score += (x1 - psr * x3) * (x2 - psr * x3) * f1
            self.RL_get.setdefault("get_by_contest", {}).setdefault(contest_id, {})
            self.RL_get["get_by_contest"][contest_id]["score"] = (x1 - psr * x3) * (x2 - psr * x3) * f1
        score = max(-10000, min(score, 10000))
        self.ls_sc = score
        self.RL_score = score
        idx = 0
        while score >= self.colorSpan[0][idx][0]:
            idx += 1
        if idx != 0: idx -= 1
        if idx == 7:
            if len(self.user.username) > 1:
                self.userSpan = self.colorSpan[0][idx][1].format(self.user.username[0], self.user.username[1:])
            else:
                self.userSpan = self.colorSpan[0][idx][1].format(self.user.username, self.user.username)
        else:
            self.userSpan = self.colorSpan[0][idx][1].format(self.user.username)
        self.save()

    def add_accepted_problem_number(self):
        self.accepted_number = models.F("accepted_number") + 1
        self.save()

    def add_submission_number(self):
        self.submission_number = models.F("submission_number") + 1
        self.save()

    # 计算总分时， 应先减掉上次该题所得分数， 然后再加上本次所得分数
    def add_score(self, this_time_score, last_time_score=None):
        last_time_score = last_time_score or 0
        self.total_score = models.F("total_score") - last_time_score + this_time_score
        self.save()

    class Meta:
        db_table = "user_profile"
