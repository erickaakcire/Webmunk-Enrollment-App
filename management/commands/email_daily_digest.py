# pylint: disable=no-member,line-too-long

from __future__ import print_function

import datetime
# import json
import re
import statistics

# import requests

from django.conf import settings
# from django.core.mail import send_mail, EmailMultiAlternatives
from django.core.management.base import BaseCommand
# from django.template.loader import render_to_string
# from django.urls import reverse
from django.utils import timezone

from ...models import RuleMatchCount

class Command(BaseCommand):
    help = 'Sends daily system health digest.'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options): # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        now = timezone.now()

        today_start = now - datetime.timedelta(days=1)
        week_start = now - datetime.timedelta(days=30)

        ignore_patterns = []

        try:
            ignore_patterns = settings.DIGEST_IGNORE_RULE_PATTERNS
        except AttributeError:
            pass

        urls = RuleMatchCount.objects.all().order_by('url').values_list('url', flat=True).distinct()

        patterns = RuleMatchCount.objects.all().order_by('pattern').values_list('pattern', flat=True).distinct()

        for ignore_pattern in ignore_patterns:
            pattern = re.compile(ignore_pattern)

            patterns = [item for item in patterns if pattern.match(item) is None]

        ok_count = 0
        not_ok_count = 0

        for url in urls: # pylint: disable=too-many-nested-blocks
            url_ok_count = 0
            url_not_ok_count = 0

            for pattern in patterns:
                if RuleMatchCount.objects.filter(url=url, pattern=pattern, matches__gt=0, checked__gte=week_start).count() > 0:
                    all_counts = []
                    today_counts = []
                    not_today_counts = []

                    for match_count in RuleMatchCount.objects.filter(url=url, pattern=pattern, checked__gte=week_start):
                        if match_count.checked > today_start:
                            today_counts.append(match_count.matches)
                        else:
                            not_today_counts.append(match_count.matches)

                        all_counts.append(match_count.matches)

                    if len(not_today_counts) > 0:
                        # not_today_sum = sum(not_today_counts)
                        not_today_mean = statistics.mean(not_today_counts)
                        not_today_mode = statistics.mode(not_today_counts)

                        last_seen = RuleMatchCount.objects.filter(url=url, pattern=pattern, matches__gt=0).order_by('-checked').first()

                        if len(today_counts) > 0:
                            today_sum = sum(today_counts)
                            # today_mean = statistics.mean(today_counts)
                            # today_mode = statistics.mode(today_counts)

                            if today_sum == 0:
                                print('%s / %s: %.3f matches today. Other days mean: %.3f, mode: %.3f, last seen: %s, last count: %d' % (url, pattern, today_sum, not_today_mean, not_today_mode, last_seen.checked.date(), last_seen.matches))

                                url_not_ok_count += 1
                                not_ok_count += 1
                            else:
                                not_today_nonzero_counts = [item for item in not_today_counts if item > 0]

                                if len(not_today_nonzero_counts) > 1:
                                    not_today_nonzero_mean = statistics.mean(not_today_nonzero_counts)
                                    not_today_nonzero_std = statistics.stdev(not_today_nonzero_counts)

                                    today_nonzero_mean = statistics.mean([item for item in today_counts if item > 0])

                                    if today_nonzero_mean < (not_today_nonzero_mean - (2 * not_today_nonzero_std)):
                                        print('%s / %s: Today (%.3f) less than lower standard deviation bound (%.3f / %.3f)' % (url, pattern, today_nonzero_mean, (not_today_nonzero_mean - not_today_nonzero_std), not_today_nonzero_mean,))

                                        url_not_ok_count += 1
                                        not_ok_count += 1
                                    else:
                                        ok_count += 1
                                        url_ok_count += 1
                                else:
                                    ok_count += 1
                                    url_ok_count += 1
                        elif len(not_today_counts) > 0:
                            print('%s / %s: 0 matches today. Other days mean: %.3f, mode: %.3f, last seen: %s, last count: %d' % (url, pattern, not_today_mean, not_today_mode, last_seen.checked.date(), last_seen.matches))

                            url_not_ok_count += 1
                            not_ok_count += 1

            if url_ok_count > 0 or url_not_ok_count > 0:
                print('%s: OK: %d, NOT OK: %d' % (url, url_ok_count, url_not_ok_count))

        print('ALL:  OK: %d, NOT OK: %d' % (ok_count, not_ok_count,))

#        now = timezone.now()
#
#        distant_future = now + datetime.timedelta(days=(100 * 365))
#
#        for enrollment in Enrollment.objects.exclude(contact_after__gte=timezone.now()): # pylint: disable=too-many-nested-blocks
#            raw_identifier = enrollment.current_raw_identifier()
#
#            if '@' in raw_identifier:
#                days_enrolled = (now - enrollment.enrolled).days
#
#                if days_enrolled >= settings.WEBMUNK_STUDY_DAYS:
#                    if (now - enrollment.last_fetched).days < 2:
#                        request_email_subject = render_to_string('reminders/email_complete_subject.txt')
#                        request_email_txt = render_to_string('reminders/email_complete_body.txt')
#
#                        context = {
#                            'settings': settings
#                        }
#
#                        request_email_html = render_to_string('reminders/email_complete_body_html.txt', context=context)
#
#                        message = EmailMultiAlternatives(request_email_subject, request_email_txt, settings.AUTOMATED_EMAIL_FROM_ADDRESS, [raw_identifier])
#                        message.attach_alternative(request_email_html, 'text/html')
#                        message.send()
#
#                        enrollment.contact_after = distant_future
#                        enrollment.save()
#                else:
#                    tasks = enrollment.tasks.filter(completed=None, active__lte=now).order_by('active', 'task')
#
#                    if tasks.count() > 0:
#                        context = {
#                            'identifier': enrollment.assigned_identifier,
#                            'tasks': [],
#                            'unsubscribe': '%s%s' % (settings.SITE_URL, reverse('unsubscribe_reminders', args=[enrollment.assigned_identifier]))
#                        }
#
#                        for task in tasks:
#                            task_url = task.url
#
#                            headers = {'Authorization': 'Bearer ' + settings.BITLY_ACCESS_CODE}
#
#                            post_data = {'long_url': task.url}
#
#                            fetch_url = 'https://api-ssl.bitly.com/v4/shorten'
#
#                            fetch_request = requests.post(fetch_url, headers=headers, json=post_data, timeout=300)
#
#                            if fetch_request.status_code >= 200 and fetch_request.status_code < 300:
#                                task_url = fetch_request.json()['link']
#
#                            if task.slug == 'upload-amazon-final':
#                                task.task = 'Update your Amazon order history'
#                                task.save()
#
#                            context['tasks'].append({
#                                'slug': task.slug,
#                                'name': task.task,
#                                'url': task_url
#                            })
#
#                        request_email_subject = render_to_string('reminders/email_reminder_subject.txt', context=context)
#                        request_email = render_to_string('reminders/email_reminder_body.txt', context=context)
#
#                        send_mail(request_email_subject, request_email, settings.AUTOMATED_EMAIL_FROM_ADDRESS, [raw_identifier], fail_silently=False)
#
#                        enrollment.contact_after = timezone.now() + datetime.timedelta(days=settings.WEBMUNK_REMINDER_DAYS_INTERVAL)
#                        enrollment.save()
#
#                        print('Sent task reminder to %s (%d tasks): %s' % (enrollment.assigned_identifier, tasks.count(), json.dumps(context['tasks'], indent=2)))
#
