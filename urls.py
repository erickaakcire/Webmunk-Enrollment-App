# pylint: disable=line-too-long

from django.conf.urls import url

from .views import enroll, uninstall, enrollments

urlpatterns = [
    url(r'^enroll.json$', enroll, name='enroll'),
    url(r'^uninstall$', uninstall, name='uninstall'),
    url(r'^enrollments$', enrollments, name='enrollments'),
]
