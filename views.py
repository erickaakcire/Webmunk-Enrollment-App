# pylint: disable=line-too-long, no-member

import csv
import datetime
import decimal
import io
import json
import re
import traceback

import chardet

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, Http404
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import Enrollment, EnrollmentGroup, ExtensionRuleSet, ScheduledTask, AmazonReward
from .simple_data_export_api import compile_data_export

@csrf_exempt
def enroll(request): # pylint: disable=too-many-branches
    raw_identifier = request.POST.get('identifier', request.GET.get('identifier', None))

    payload = {}

    now = timezone.now()

    if raw_identifier is not None:
        raw_identifier = raw_identifier.strip().lower()

        found_enrollment = None

        for enrollment in Enrollment.objects.all().order_by('assigned_identifier'):
            if raw_identifier in (enrollment.current_raw_identifier().strip().lower(), enrollment.assigned_identifier,):
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
            traceback.print_exc()

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
def amazon_fetched(request): # pylint: disable=too-many-branches
    raw_identifier = request.POST.get('identifier', request.GET.get('identifier', None))

    payload = {
        'updated': 0
    }

    if raw_identifier is not None:
        now = timezone.now()

        for enrollment in Enrollment.objects.all():
            if raw_identifier in (enrollment.current_raw_identifier(), enrollment.assigned_identifier,):
                payload['updated'] += enrollment.tasks.filter(slug__icontains='amazon-fetch', completed=None, active__lte=now).update(completed=now)

                if enrollment.tasks.filter(slug__icontains='amazon-fetch').exclude(completed=None).count() > 1 and enrollment.tasks.filter(slug='main-survey-final').count() == 0:
                    survey_url = 'https://hbs.qualtrics.com/jfe/form/SV_37xQ9ZpbqC75UVg?webmunk_id=%s' % enrollment.assigned_identifier

                    ScheduledTask.objects.create(enrollment=enrollment, active=now, task='Complete Final Survey', slug='main-survey-final', url=survey_url)

    return HttpResponse(json.dumps(payload, indent=2), content_type='application/json', status=200)

@csrf_exempt
def mark_eligible(request): # pylint: disable=too-many-branches
    raw_identifier = request.POST.get('identifier', request.GET.get('identifier', None))

    if raw_identifier is not None:
        now = timezone.now()

        for enrollment in Enrollment.objects.all():
            if raw_identifier in (enrollment.current_raw_identifier(), enrollment.assigned_identifier,):
                metadata = enrollment.fetch_metadata()

                is_eligible = metadata.get('is_eligible', False)

                if is_eligible is False:
                    metadata['is_eligible'] = now.isoformat()

                    enrollment.metadata = json.dumps(metadata, indent=2)
                    enrollment.save()

    return render(request, 'webmunk_eligible.html')


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
    filename = compile_data_export('enrollment.enrollments', [])

    if filename is not None:
        with open(filename, 'rb') as open_file:
            response = HttpResponse(open_file, content_type='text/csv', status=200)
            response['Content-Disposition'] = 'attachment; filename= "webmunk-enrollments.txt"'

            return response

    raise Http404

@staff_member_required
def enrollment_upload_rewards(request): # pylint: disable=unused-argument, too-many-branches, too-many-statements, too-many-locals
    payload = {
        'message': 'Error uploading file.'
    }

    if request.method == 'POST':
        input_file = request.FILES['purchase_upload']

        added = 0

        raw_data = input_file.read()

        result = chardet.detect(raw_data)

        input_file.seek(0)

        with io.TextIOWrapper(input_file, encoding=result['encoding']) as text_file:
            csv_in = csv.reader(text_file)

            for row in list(csv_in)[1:]:
                identifier = row[1]
                wishlist_url = row[5]

                item_price = row[26]
                item_name = row[25]
                item_url = row[24]
                item_type = row[23]

                notes = row[29]

                if item_name.strip() != '':
                    enrollment = Enrollment.objects.filter(assigned_identifier=identifier).first()

                    if enrollment is not None:
                        reward = AmazonReward.objects.filter(participant=enrollment, item_url=item_url).first()

                        if reward is None:
                            reward = AmazonReward(participant=enrollment, item_url=item_url)

                            reward.wishlist_url = wishlist_url
                            reward.item_type = item_type
                            reward.item_name = item_name

                            stripped_price = re.sub(r'[^\d.]', '', item_price)

                            if stripped_price != '':
                                float_price = float(decimal.Decimal(stripped_price))

                                reward.item_price = float_price

                            reward.notes = notes

                            reward.save()

                            added += 1

        payload['message'] = '%d items added.' % added

    return HttpResponse(json.dumps(payload, indent=2), content_type='application/json', status=200)

def enrollments_rewards_json(request): # pylint: disable=unused-argument, too-many-branches, too-many-statements
    payload = {}

    identifier = request.GET.get('webmunk_id', '')

    enrollment = Enrollment.objects.filter(assigned_identifier=identifier).first()

    if enrollment is not None:
        reward_index = 1

        for reward in enrollment.rewards.all():
            payload['full_name_product%d' % reward_index] = reward.item_name

            payload['asin_product%d' % reward_index] = reward.fetch_asin()

            payload['short_name_product%d' % reward_index] = ' '.join(reward.item_name.split()[:4])

    return HttpResponse(json.dumps(payload, indent=2), content_type='application/json', status=200)
