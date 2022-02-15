# pylint: disable=line-too-long

from django.conf.urls import url
from django.contrib.auth.views import LogoutView
from django.conf import settings

from .views import enroll

urlpatterns = [
    url(r'^enroll.json$', enroll, name='enroll'),
]
