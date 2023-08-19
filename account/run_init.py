import os
import django
from ..oj import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings)
django.setup()

from models import UserProfile

def initUserProfile():
    user_profiles = UserProfile.objects.all()
    for up in user_profiles:
        up.initModels()

if __name__ == '__main__':
    initUserProfile()
