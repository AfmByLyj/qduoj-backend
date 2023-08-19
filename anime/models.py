from django.db import models
from account.models import User
from django.conf import settings
from utils.models import JSONField

class Status(object):
    ENDED = "Completed"
    NOTSTART = "Not start"
    SERIALIZING = "Serializing"

class Category(object):
    ANIME = "animation"
    TEACHING = "teaching"

class AnimeFormat(object):
    IFRAME = "iframe"
    MP4URL = "mp4"
    M3U8URL = "m3u8"

class Anime(models.Model):
    create_time = models.DateTimeField(auto_now_add=True)   # 创建日期
    update_time = models.DateTimeField(auto_now=True)       # 更新日期
    anime_name = models.TextField()                         # 名称
    anime_id = models.TextField(unique=True)                # 唯一标签
    episodes = JSONField(default=dict)                      # 线路+分集 <int, int>
    coverImg = models.TextField(default=f"{settings.ANIME_URI_PREFIX}/default.png") # 封面
    uploader = models.ForeignKey(User, on_delete=models.CASCADE)                    # 绑定上传用户
    status = models.TextField(default=Status.NOTSTART)        # 状态
    description = models.TextField()                        # 描述
    category = models.TextField(default=Category.TEACHING)  # 分类描述，ANIME为隐藏资源，TEACHING为可见资源

    def modify_name(self, new_name):    # 名称重命名
        self.anime_name = new_name
        self.save()

    def modify_cover(self, new_cover_url=None):
        url = new_cover_url or f"{settings.ANIME_URI_PREFIX}/default.jpg"
        self.coverImg = url
        self.save()

    def modify_episodes(self, roads, episodes_increment=0):
        self.episodes[roads] += episodes_increment
        self.save()

    def StatusToSerializing(self):
        self.status = Status.SERIALIZING
        self.save()

    def StatusToEnd(self):
        self.status = Status.ENDED
        self.save()
    
    def modify_category(self, is_display=True):
        self.category = Category.TEACHING if is_display else Category.ANIME
        self.save()

    class Meta:
        db_table = "Anime"

class AnimeDetail(models.Model):
    father = models.ForeignKey(Anime, on_delete=models.CASCADE) # 父级对象
    father_road = models.IntegerField(null=False)   # 父级线路
    father_episode = models.IntegerField(null=False)    # 所属集，正数为正片，负数为特别片
    anime_format = models.TextField(null=False)     # 视频格式，iframe标签，MP4链接，m3u8链接
    anime_resource = models.TextField(null=False)   # 视频资源链接，以format为准
    title = models.TextField(default="Unknow")

    def modify_format(self, index):
        if index == 0:
            self.anime_format = AnimeFormat.IFRAME
        elif index == 1:
            self.anime_format = AnimeFormat.MP4URL
        else:
            self.anime_format = AnimeFormat.M3U8URL
        self.save()
    
    def modify_resource(self, url):
        self.anime_resource = url
        self.save()

    def getLink(self):
        return {
            'format': self.anime_format,
            'url': self.anime_resource
        }
    
    class Meta:
        db_table = "AnimeDetail"