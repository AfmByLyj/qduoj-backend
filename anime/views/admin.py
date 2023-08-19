from utils.api import APIView
from ..models import Anime, AnimeDetail, Category
from account.decorators import login_required
from ..serializers import ImageUploadForm
from django.conf import settings
from utils.shortcuts import rand_str, img2base64, datetime2str
import os, base64


class createAnime(APIView):
    def put(self, request):
        data = request.data
        anime_name = data["anime_name"]
        anime_id = data["anime_id"]
        pid = data["pid"]
        if not anime_name:
            return self.error("Need animation name!")
        if not anime_id:
            return self.error("Need animation ID!")
        if pid != anime_id:
            if Anime.objects.filter(anime_id=anime_id).exists():
                return self.error("Animation ID already exists")
        if not request.user:
            return self.error("Please login")
        try:
            selectAnime = Anime.objects.get(anime_id=anime_id)
            selectAnime.episodes = data["episodes"]
            selectAnime.description = data["description"]
            selectAnime.status = data["status"]
            selectAnime.anime_name = anime_name
            selectAnime.anime_id = anime_id
            detail = data['detail']
            for road, ep in data["episodes"].items():
                for _ in range(1, ep + 1):
                    selDetail = detail[road][_]
                    title = selDetail['title']
                    formats = selDetail['format']
                    url = selDetail['url']
                    foo, zoo = AnimeDetail.objects.get_or_create(father=selectAnime, father_road=road, father_episode=_)
                    foo.anime_format = formats
                    foo.anime_resource = url
                    foo.title = title
                    foo.save()
            selectAnime.save()
        except Exception as e:
            return self.error('Save data error')

        return self.success("Completed")

    def post(self, request):
        data = request.data
        anime_name = data["anime_name"]
        anime_id = data["anime_id"]
        if not anime_name:
            return self.error("Need animation name!")
        if not anime_id:
            return self.error("Need animation ID!")

        if Anime.objects.filter(anime_id=anime_id).exists():
            return self.error("Animation ID already exists")
        if not request.user:
            return self.error("Please login")
        data["uploader"] = request.user
        data["episodes"] = {1: 0}
        
        anime = Anime.objects.create(**data)
        return self.success("Create Completed")
    
class AnimeCoverAPI(APIView):
    @login_required
    def post(self, request):  
        data = request.data 
        anime_id = data["anime_id"]
        if not anime_id:
            return self.error("Need animation ID!")
        
        coverBase64 = data['cover']
        size = data['size']
        suffix = data['suffix']

        if not coverBase64 or not size or not suffix:
            return self.error("Data is Missing!")

        if size > 5 * 1024 * 1024:
            return self.error("Picture is too large")
        suffix = suffix.lower()
        if suffix not in ["jpg", "jpeg", "png"]:
            return self.error("Unsupported file format")

        try:
            # name = rand_str(10) + '.' + suffix
            # with open(os.path.join(settings.ANIME_UPLOAD_DIR, name), "wb") as img:
            #     coverData = base64.b64decode(coverBase64)
            #     img.write(coverData)
            anime = Anime.objects.get(anime_id=anime_id)

            anime.coverImg = coverBase64
            anime.save()
        except Exception as e:
            return self.error(str(e))
        return self.success(f"Completed")