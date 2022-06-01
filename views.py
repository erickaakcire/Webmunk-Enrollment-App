# pylint: disable=line-too-long, no-member

import json

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import Enrollment, ExtensionRuleSet, ScheduledTask

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
            settings.WEBMUNK_UPDATE_TASKS(found_enrollment, ScheduledTask)
        except AttributeError:
            pass

        try:
            settings.WEBMUNK_ASSIGN_RULES(found_enrollment, ExtensionRuleSet)
        except AttributeError:
            if found_enrollment.rule_set is None:
                selected_rules = ExtensionRuleSet.objects.filter(is_default=True).first()

                if selected_rules is not None:
                    found_enrollment.rule_set = selected_rules
                    found_enrollment.save()

        if found_enrollment.rule_set is not None and found_enrollment.rule_set.is_active:
            payload['rules'] = found_enrollment.rule_set.rules()

            tasks = []

            for task in found_enrollment.tasks.filter(completed=None, active__lte=now).order_by('active'):
                tasks.append({
                    'message':  task.task,
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
