from django import forms
from rest_framework.fields import empty
from utils.api import serializers, UsernameSerializer
from .models import Anime, AnimeDetail

class ImageUploadForm(forms.Form):
    image = forms.FileField()

class AnimeListSerializer(serializers.ModelSerializer):
    uploader = UsernameSerializer()
    class Meta:
        model = Anime
        fields = '__all__'

class AnimeSingleSerializer(serializers.ModelSerializer):
    uploader = UsernameSerializer()

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
    
    class Meta:
        model = Anime
        fields = '__all__'

class AnimeDetailSerializer(serializers.ModelSerializer):

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = AnimeDetail
        fields = '__all__'
