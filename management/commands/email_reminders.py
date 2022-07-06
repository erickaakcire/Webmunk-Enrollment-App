# pylint: disable=no-member,line-too-long

from __future__ import print_function

import datetime

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils import timezone

from ...models import Enrollment

class Command(BaseCommand):
    help = 'Sends reminders to participants with outstanding tasks.'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        now = timezone.now()

        for enrollment in Enrollment.objects.exclude(contact_after__gte=timezone.now()).filter(active__lte=now).filter(assigned_identifier='98650795'):
            raw_identifier = enrollment.current_raw_identifier()

            if '@' in raw_identifier:
                tasks = enrollment.tasks.filter(completed=None)

                if tasks.count() > 0:
                    context = {
                        'identifier': enrollment.assigned_identifier,
                        'tasks': []
                    }

                    for task in tasks:
                        context['tasks'].append({
                            'name': task.task,
                            'url': task.url
                        })

                    request_email_subject = render_to_string('reminders/email_reminder_subject.txt', context=context)
                    request_email = render_to_string('reminders/email_reminder_body.txt', context=context)

                    send_mail(request_email_subject, request_email, settings.AUTOMATED_EMAIL_FROM_ADDRESS, [raw_identifier], fail_silently=False)

                    enrollment.contact_after = timezone.now() + datetime.timedelta(days=settings.WEBMUNK_REMINDER_DAYS_INTERVAL)
                    enrollment.save()

                    print('Sent task reminder to %s.' % enrollment.assigned_identifier)
