# pylint: disable=line-too-long

from django.conf.urls import url

from .views import enroll, uninstall, enrollments, unsubscribe_reminders, enrollments_txt

urlpatterns = [
    url(r'^enroll.json$', enroll, name='enroll'),
    url(r'^uninstall$', uninstall, name='uninstall'),
    url(r'^unsubscribe/(?P<identifier>.+)$', unsubscribe_reminders, name='unsubscribe_reminders'),
    url(r'^enrollments$', enrollments, name='enrollments'),
    url(r'^enrollments.txt$', enrollments_txt, name='enrollments_txt'),
]
