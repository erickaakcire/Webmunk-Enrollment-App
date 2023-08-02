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

from ...models import Enrollment

class Command(BaseCommand):
    help = 'Verifies whether scheduled Qualtrics surveys have been completed'

    @add_qs_arguments
    def add_arguments(self, parser):
        pass

    @handle_lock
    @handle_schedule
    def handle(self, *args, **options): # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        for survey_id in settings.WEBMUNK_QUALTRICS_ELIGIBILITY_SURVEY_IDS:
            start_url = '%s/API/v3/surveys/%s/export-responses' % (survey_id[2], survey_id[0])

            data = { 'format': 'json' }

            headers = {
                'Content-type': 'application/json',
                'Accept': 'text/plain',
                'X-API-TOKEN':  survey_id[3]
            }

            response = requests.post(start_url, data=json.dumps(data), headers=headers, timeout=300)

            if response.status_code == 200:
                response_json = response.json()

                progress_id = response_json.get('result', {}).get('progressId', None)

                if progress_id is not None:
                    progress_url = '%s/API/v3/surveys/%s/export-responses/%s' % (survey_id[2], survey_id[0], progress_id)

                    headers = {
                        'X-API-TOKEN':  survey_id[3]
                    }

                    status = 'inProgress'
                    file_id = None

                    while status == 'inProgress':
                        time.sleep(15)

                        progress_response = requests.get(progress_url, headers=headers, timeout=300)

                        if progress_response.status_code == 200:
                            progress_json = progress_response.json()

                            status = progress_json.get('result', {}).get('status', 'failed')
                            file_id = progress_json.get('result', {}).get('fileId', None)
                        else:
                            print('PROGRESS NON-200 HTTP CODE: %d -- %s' % (progress_response.status_code, progress_url))
                            status = '404'

                    if status == 'complete' and file_id is not None:
                        download_url = '%s/API/v3/surveys/%s/export-responses/%s/file' % (survey_id[2], survey_id[0], file_id)

                        headers = {
                            'X-API-TOKEN':  survey_id[3]
                        }

                        file_response = requests.get(download_url, headers=headers, timeout=300)

                        with io.BytesIO(file_response.content) as zip_in:
                            with zipfile.ZipFile(zip_in) as zip_file:
                                for name in zip_file.namelist():
                                    if name.endswith('.json'):
                                        with zip_file.open(name) as export_file:
                                            response_file = json.load(export_file)

                                            for survey_response in response_file.get('responses', []): # pylint: disable=too-many-nested-blocks
                                                # if survey_response.get('values', {}).get('finished', 0) == 1:
                                                email_address = survey_response.get('values', {}).get('QID26_TEXT', None)

                                                if email_address is not None:
                                                    for enrollment in Enrollment.objects.all():
                                                        if enrollment.current_raw_identifier().lower() == email_address.lower():
                                                            # print('FOUND %s -- %s...' % (email_address, enrollment.assigned_identifier))
                                                            metadata = enrollment.fetch_metadata()

                                                            is_eligible = metadata.get('is_eligible', False)

                                                            if is_eligible is False:
                                                                metadata['is_eligible'] = timezone.now().isoformat()

                                                                enrollment.metadata = json.dumps(metadata, indent=2)
                                                                enrollment.save()

                                                                print('NOW ELIGIBLE %s...' % email_address)
