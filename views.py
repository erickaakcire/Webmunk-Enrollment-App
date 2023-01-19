# pylint: disable=line-too-long, no-member

import csv
import datetime
import io
import json

import pytz

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, Http404
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import Enrollment, EnrollmentGroup, ExtensionRuleSet, ScheduledTask

@csrf_exempt
def enroll(request): # pylint: disable=too-many-branches
    raw_identifier = request.POST.get('identifier', request.GET.get('identifier', None))

    payload = {}

    now = timezone.now()

    if raw_identifier is not None:
        found_enrollment = None

        for enrollment in Enrollment.objects.all():
            if raw_identifier in (enrollment.current_raw_identifier(), enrollment.assigned_identifier,):
                found_enrollment = enrollment

                break

        if found_enrollment is None:
            found_enrollment = Enrollment(enrolled=now, last_fetched=now)

            found_enrollment.assign_random_identifier(raw_identifier)
            found_enrollment.save()
        else:
            found_enrollment.last_fetched = now
            found_enrollment.save()

        payload['identifier'] = found_enrollment.assigned_identifier

        payload['rules'] = {
            'rules': [],
            'additional-css': [],
            'actions': {},
        }

        try:
            settings.WEBMUNK_ASSIGN_RULES(found_enrollment, ExtensionRuleSet)
        except AttributeError:
            if found_enrollment.rule_set is None:
                selected_rules = ExtensionRuleSet.objects.filter(is_default=True).first()

                if selected_rules is not None:
                    found_enrollment.rule_set = selected_rules
                    found_enrollment.save()

        try:
            settings.WEBMUNK_UPDATE_TASKS(found_enrollment, ScheduledTask)
        except AttributeError:
            pass

        if found_enrollment.rule_set is not None and found_enrollment.rule_set.is_active:
            payload['rules'] = found_enrollment.rule_set.rules()

            tasks = []

            now = timezone.now()

            for task in found_enrollment.tasks.filter(completed=None, active__lte=now).order_by('active'):
                tasks.append({
                    'message': task.task,
                    "url": task.url
                })

            payload['rules']['tasks'] = tasks
        else:
            payload['error'] = 'Participant not configured with ruleset and no default ruleset selected.'
    else:
        payload['error'] = 'Unable to retrieve original raw identifier from the request. Please fix and try again.'

    try:
        settings.WEBMUNK_UPDATE_ALL_RULE_SETS(payload)
    except AttributeError:
        pass

    return HttpResponse(json.dumps(payload, indent=2), content_type='application/json', status=200)

@csrf_exempt
def uninstall(request): # pylint: disable=too-many-branches
    raw_identifier = request.POST.get('identifier', request.GET.get('identifier', None))

    now = timezone.now()

    if raw_identifier is not None:
        found_enrollment = None

        for enrollment in Enrollment.objects.all():
            if raw_identifier in (enrollment.current_raw_identifier(), enrollment.assigned_identifier,):
                found_enrollment = enrollment

                break

        if found_enrollment is not None:
            found_enrollment.last_uninstalled = now
            found_enrollment.save()

            return render(request, 'webmunk_uninstall.html')

    raise Http404

@csrf_exempt
def privacy(request): # pylint: disable=too-many-branches
    return render(request, 'webmunk_privacy.html')

@staff_member_required
def enrollments(request):
    context = {
        'enrollments': Enrollment.objects.all().order_by('-enrolled'),
        'groups': EnrollmentGroup.objects.all().order_by('name'),
    }

    return render(request, 'webmunk_enrollments.html', context=context)

def unsubscribe_reminders(request, identifier):
    context = {}

    later = timezone.now() + datetime.timedelta(days=(365 * 250))

    Enrollment.objects.filter(assigned_identifier=identifier).update(contact_after=later)

    return render(request, 'webmunk_unsubscribe_reminders.html', context=context)

def update_group(request):
    payload = {
        'message': 'Group not updated.'
    }

    if request.method == 'POST':
        identifier = request.POST.get('identifier', None)
        group = request.POST.get('group', None)

        enrollment = Enrollment.objects.filter(assigned_identifier=identifier).first()
        group = EnrollmentGroup.objects.filter(name=group).first()

        if enrollment is not None:
            enrollment.group = group
            enrollment.save()

            payload['message'] = 'New group for %s: %s' % (enrollment, group)

    return HttpResponse(json.dumps(payload, indent=2), content_type='application/json', status=200)

@staff_member_required
def enrollments_txt(request): # pylint: disable=unused-argument, too-many-branches, too-many-statements
    output = io.StringIO()

    writer = csv.writer(output, delimiter='\t')

    header = [
        'ID',
        'Group',
        'Original ID',
        'Rule Set',
        'Enrolled',
        'History Since',
        'Last Updated',
        'Latest Data Point',
        'Uninstalled',
        'Intake Survey Completed',
        'First Amazon History Uploaded',
        'First Amazon Upload Count',
        'Final Amazon History Uploaded',
        'Final Amazon Upload Count',
        'Final Survey Completed',
    ]

    here_tz = pytz.timezone(settings.TIME_ZONE)

    writer.writerow(header)

    for enrollment in Enrollment.objects.all().order_by('assigned_identifier'):
        enrollment_values = []

        enrollment_values.append(enrollment.assigned_identifier)

        if enrollment.group is not None:
            enrollment_values.append(enrollment.group.name)
        else:
            enrollment_values.append('')

        enrollment_values.append(enrollment.current_raw_identifier())
        enrollment_values.append(str(enrollment.rule_set))

        enrollment_values.append(enrollment.enrolled.astimezone(here_tz).strftime('%Y-%m-%d %H:%M'))

        metadata = enrollment.fetch_metadata()

        enrollment_values.append(metadata.get('amazon_start', ''))

        if enrollment.last_fetched is not None:
            enrollment_values.append(enrollment.last_fetched.astimezone(here_tz).strftime('%Y-%m-%d %H:%M'))
        else:
            enrollment_values.append('')

        latest_data_point = enrollment.latest_data_point()

        if latest_data_point is not None:
            enrollment_values.append(latest_data_point.astimezone(here_tz).strftime('%Y-%m-%d %H:%M'))
        else:
            enrollment_values.append('')

        if enrollment.last_uninstalled is not None:
            enrollment_values.append(enrollment.last_uninstalled.astimezone(here_tz).strftime('%Y-%m-%d %H:%M'))
        else:
            enrollment_values.append('')

        task = enrollment.tasks.filter(slug='qualtrics-initial').exclude(completed=None).first()

        if task is not None:
            enrollment_values.append(task.completed.astimezone(here_tz).strftime('%Y-%m-%d %H:%M'))
        else:
            enrollment_values.append('')

        task = enrollment.tasks.filter(slug='upload-amazon-start').exclude(completed=None).first()

        if task is not None:
            enrollment_values.append(task.completed.astimezone(here_tz).strftime('%Y-%m-%d %H:%M'))

            metadata = {}

            if task.metadata is not None and task.metadata != '':
                metadata = json.loads(task.metadata)

            item_count = metadata.get('item_count', '')

            enrollment_values.append(str(item_count))
        else:
            enrollment_values.append('')
            enrollment_values.append('')

        task = enrollment.tasks.filter(slug='upload-amazon-final').exclude(completed=None).first()

        if task is not None:
            enrollment_values.append(task.completed.astimezone(here_tz).strftime('%Y-%m-%d %H:%M'))

            metadata = {}

            if task.metadata is not None and task.metadata != '':
                metadata = json.loads(task.metadata)

            item_count = metadata.get('item_count', '')

            enrollment_values.append(str(item_count))

        else:
            enrollment_values.append('')
            enrollment_values.append('')

        task = enrollment.tasks.filter(slug='qualtrics-final').exclude(completed=None).first()

        if task is not None:
            enrollment_values.append(task.completed.astimezone(here_tz).strftime('%Y-%m-%d %H:%M'))
        else:
            enrollment_values.append('')

        # enrollment_values.append('-')

        writer.writerow(enrollment_values)

    response = HttpResponse(output.getvalue(), content_type='text/csv', status=200)
    response['Content-Disposition'] = 'attachment; filename= "webmunk-enrollments.txt"'

    return response
