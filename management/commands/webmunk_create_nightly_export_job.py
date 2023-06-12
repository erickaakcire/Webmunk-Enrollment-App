# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

import datetime
import json

import arrow
import pytz

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from simple_data_export.models import ReportJobBatchRequest

from ...models import Enrollment

class Command(BaseCommand):
    help = 'Creates a nightly job to upload data to the cloud.'

    def add_arguments(self, parser):
        parser.add_argument('--date',
                            type=str,
                            dest='date',
                            help='Date of app usage in YYY-MM-DD format')

    def handle(self, *args, **options): # pylint: disable=too-many-locals,too-many-branches,too-many-statements
        now = timezone.now().astimezone(pytz.timezone(settings.TIME_ZONE))

        if options['date'] is not None:
            now = arrow.get(options['date'] + 'T23:59:59+00:00').datetime

        requester = get_user_model().objects.get(username='s3-backup')

        yesterday = now.date() - datetime.timedelta(days=1)

        active_users = []

        for source in Enrollment.objects.all().order_by('assigned_identifier'):
            if (source.assigned_identifier in active_users) is False:
                active_users.append(source.assigned_identifier)

        parameters = {}
        parameters['data_sources'] = active_users

        parameters['data_types'] = [
            'enrollment.qualtrics_responses',
            'enrollment.scheduled_tasks',
        ]

        parameters['start_time'] = yesterday.isoformat()
        parameters['end_time'] = yesterday.isoformat()
        parameters['custom_parameters'] = {
            'path': yesterday.isoformat()
        }

        # ReportJobBatchRequest.objects.create(requester=requester, requested=now, parameters=json.dumps(parameters, indent=2))

        requester = get_user_model().objects.get(username='s3-enrollments')

        active_users = []

        for source in Enrollment.objects.all().order_by('assigned_identifier'):
            if (source.assigned_identifier in active_users) is False:
                active_users.append(source.assigned_identifier)

        parameters = {}
        parameters['data_sources'] = active_users

        parameters['data_types'] = [
            'enrollment.enrollments',
        ]

        parameters['start_time'] = yesterday.isoformat()
        parameters['end_time'] = yesterday.isoformat()
        parameters['custom_parameters'] = {
            'path': yesterday.isoformat()
        }

        ReportJobBatchRequest.objects.create(requester=requester, requested=now, parameters=json.dumps(parameters, indent=2))
