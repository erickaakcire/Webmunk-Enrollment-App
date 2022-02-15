# pylint: disable=line-too-long

from django.conf.urls import url

from .views import enroll

urlpatterns = [
    url(r'^enroll.json$', enroll, name='enroll'),
]
