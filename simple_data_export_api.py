# pylint: disable=line-too-long, no-member

import io
import json
import os
import tempfile
import time
import zipfile

from past.utils import old_div

import arrow
import requests

from django.conf import settings

from .models import Enrollment

def export_data_sources(params=None):
    if params is None:
        params = {}

    data_sources = []

    for enrollment in Enrollment.objects.all():
        if (enrollment.assigned_identifier in data_sources) is False:
            data_sources.append(enrollment.assigned_identifier)

    return data_sources

def export_data_types():
    return [
        ('enrollment.qualtrics_responses', 'Qualtrics Responses',),
    ]

def compile_data_export(data_type, data_sources, start_time=None, end_time=None, custom_parameters=None): # pylint: disable=too-many-locals, unused-argument, too-many-branches
    if data_type == 'enrollment.qualtrics_responses':
        now = arrow.get()

        zip_filename = tempfile.gettempdir() + os.path.sep + 'qualtrics_responses' + str(now.timestamp()) + str(old_div(now.microsecond, 1e6)) + '.zip'

        with zipfile.ZipFile(zip_filename, 'w', allowZip64=True) as export_file:
            for survey in settings.WEBMUNK_QUALTRICS_EXPORT_SURVEY_IDS:
                start_url = '%s/API/v3/surveys/%s/export-responses' % (survey[2], survey[0])

                data = { 'format': 'tsv' }

                headers = {
                    'Content-type': 'application/json',
                    'Accept': 'text/plain',
                    'X-API-TOKEN':  survey[3]
                }

                response = requests.post(start_url, data=json.dumps(data), headers=headers, timeout=300)

                if response.status_code == 200:
                    response_json = response.json()

                    progress_id = response_json.get('result', {}).get('progressId', None)

                    if progress_id is not None:
                        progress_url = '%s/API/v3/surveys/%s/export-responses/%s' % (survey[2], survey[0], progress_id)

                        headers = {
                            'X-API-TOKEN':  survey[3]
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
                            download_url = '%s/API/v3/surveys/%s/export-responses/%s/file' % (survey[2], survey[0], file_id)

                            headers = {
                                'X-API-TOKEN':  survey[3]
                            }

                            file_response = requests.get(download_url, headers=headers, timeout=300)

                            with io.BytesIO(file_response.content) as zip_in:
                                with zipfile.ZipFile(zip_in) as zip_file:
                                    for name in zip_file.namelist():
                                        if name.endswith('.tsv'):
                                            with zip_file.open(name) as inner_file:
                                                export_file.writestr(name, inner_file.read())

        return zip_filename

    return None
