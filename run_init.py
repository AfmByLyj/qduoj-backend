import os
import django
from oj import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oj.settings")
django.setup()

from account.models import UserProfile

def initUserProfile():
    user_profiles = UserProfile.objects.all()
    for up in user_profiles:
        up.ls_sc = 1000
        up.save()
        up.initModels()

if __name__ == '__main__':
    initUserProfile()
