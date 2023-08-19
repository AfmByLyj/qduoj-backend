from django.conf.urls import url
from ..models import Anime, AnimeDetail, Category
from ..views.admin import createAnime, AnimeCoverAPI


urlpatterns = [
    url(r"^create/anime/?$", createAnime.as_view(), name="create_anime"),
    url(r"^uploadCover/?$", AnimeCoverAPI.as_view(), name="upload_cover")
]