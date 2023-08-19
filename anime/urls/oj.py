from django.conf.urls import url
from ..views.oj import AnimeList, AnimeDetails

urlpatterns = [
    url(r"^anime/?$", AnimeList.as_view(), name="animation_List"),
    url(r"^animeDetail/?$", AnimeDetails.as_view(), name="animation_detail")
]