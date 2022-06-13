# pylint: disable=line-too-long

from django.conf.urls import url

from .views import enroll, uninstall

urlpatterns = [
    url(r'^enroll.json$', enroll, name='enroll'),
    url(r'^uninstall$', uninstall, name='uninstall'),
]
