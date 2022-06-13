# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

import io
import json
import time
import zipfile

import requests

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from quicksilver.decorators import handle_lock, handle_schedule, add_qs_arguments

from ...models import ScheduledTask, Enrollment

class Command(BaseCommand):
    help = 'Verifies whether scheduled Qualtrics surveys have been completed'

    @add_qs_arguments
    def add_arguments(self, parser):
        pass

    @handle_lock
    @handle_schedule
    def handle(self, *args, **options): # pylint: disable=too-many-locals, too-many-branches
        now = timezone.now()

        pending_tasks = ScheduledTask.objects.filter(completed=None, active__lte=now, slug__startswith='qualtrics')
        pending_tasks.update(last_check=now)

        if pending_tasks.count() > 0: # pylint: disable=too-many-nested-blocks
            for survey_id in settings.WEBMUNK_QUALTRICS_SURVEY_IDS:
                start_url = '%s/API/v3/surveys/%s/export-responses' % (settings.WEBMUNK_QUALTRICS_BASE_URL, survey_id[0])

                data = { 'format': 'json' }

                headers = {
                    'Content-type': 'application/json',
                    'Accept': 'text/plain',
                    'X-API-TOKEN':  settings.WEBMUNK_QUALTRICS_API_TOKEN
                }

                response = requests.post(start_url, data=json.dumps(data), headers=headers)

                if response.status_code == 200:
                    response_json = response.json()

                    progress_id = response_json.get('result', {}).get('progressId', None)

                    if progress_id is not None:
                        progress_url = '%s/API/v3/surveys/%s/export-responses/%s' % (settings.WEBMUNK_QUALTRICS_BASE_URL, survey_id[0], progress_id)

                        headers = {
                            'X-API-TOKEN':  settings.WEBMUNK_QUALTRICS_API_TOKEN
                        }

                        status = 'inProgress'
                        file_id = None

                        while status == 'inProgress':
                            time.sleep(15)

                            progress_response = requests.get(progress_url, headers=headers)

                            if progress_response.status_code == 200:
                                progress_json = progress_response.json()

                                status = progress_json.get('result', {}).get('status', 'failed')
                                file_id = progress_json.get('result', {}).get('fileId', None)
                            else:
                                print('PROGRESS NON-200 HTTP CODE: %d -- %s' % (progress_response.status_code, progress_url))
                                status = '404'

                        if status == 'complete' and file_id is not None:
                            download_url = '%s/API/v3/surveys/%s/export-responses/%s/file' % (settings.WEBMUNK_QUALTRICS_BASE_URL, survey_id[0], file_id)

                            headers = {
                                'X-API-TOKEN':  settings.WEBMUNK_QUALTRICS_API_TOKEN
                            }

                            file_response = requests.get(download_url, headers=headers)

                            with io.BytesIO(file_response.content) as zip_in:
                                with zipfile.ZipFile(zip_in) as zip_file:
                                    for name in zip_file.namelist():
                                        if name.endswith('.json'):
                                            with zip_file.open(name) as export_file:
                                                response_file = json.load(export_file)

                                                for survey_response in response_file.get('responses', []):
                                                    webmunk_id = survey_response.get('values', {}).get('webmunk_id', None)

                                                    if webmunk_id is not None:
                                                        enrollment = Enrollment.objects.filter(assigned_identifier=webmunk_id).first()

                                                        if enrollment is not None:
                                                            enrollment.tasks.filter(completed=None, active__lte=now, slug=survey_id[1]).update(completed=now)
                else:
                    print('START NON-200 HTTP CODE: %d -- %s' % (response.status_code, start_url))
