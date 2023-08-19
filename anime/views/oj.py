from utils.api import APIView
from ..models import Anime, AnimeDetail, Category
from ..serializers import AnimeListSerializer, AnimeDetailSerializer, AnimeSingleSerializer
import time, json

class AnimeList(APIView):
    def get(self, request):
        timeSSA = request.GET.get("klot")
        if timeSSA:
            frontDate = self.klotTransform(timeSSA)
            if frontDate == -1:
                return self.error("Incorrect klot format")
            else:
                backendDate = int(time.time() * 1000)
                if abs(backendDate - frontDate) > 120000:
                    return self.error("Klot has expired!")
        else:
            return self.error("Need klot pst!")
        anime_type = request.GET.get("type")
        if anime_type:
            animes = Anime.objects.filter(category=Category.ANIME).order_by("-update_time")
        else:
            animes = Anime.objects.filter(category=Category.TEACHING).order_by("-update_time")
        searchName = request.GET.get("title")
        if searchName:
            animes = animes.filter(anime_name__icontains=searchName)
        status = request.GET.get("title")
        if status:
            animes = animes.filter(status=status)
        data = self.paginate_data(request=request, query_set=animes, object_serializer=AnimeListSerializer)
        return self.success(data)
    
class AnimeDetails(APIView):
    def get(self, request):
        data = request.GET
        id = data.get("id")
        if not id:
            return self.error("Need anime ID!")
        load = data.get("load")
        ep = data.get("ep")
        if not load and not ep:
            LE = Anime.objects.get(anime_id=id)
            res = AnimeDetail.objects.filter(father__anime_id=id)
            return self.success({'all': AnimeSingleSerializer(LE, user=request.user).data, 'detail': AnimeDetailSerializer(res, many=True, user=request.user).data})
            # return self.success({'all': LE})
        if not load:
            return self.error("Need anime load!")
        if not ep:
            return self.error("Need anime episode!")
        try:
            res = AnimeDetail.objects.get(father__anime_id=id, father_road=load, father_episode=ep)
        except Exception as e:
            return self.error("parameter error! {}".format(e))

        return self.success(res.getLink())