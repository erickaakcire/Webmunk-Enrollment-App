# pylint: disable=line-too-long, no-member

import csv
import io
import json
import os
import tempfile
import time
import zipfile

from past.utils import old_div

import arrow
import pytz
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
        ('enrollment.scheduled_tasks', 'Scheduled Tasks',),
        ('enrollment.enrollments', 'Enrollment Information',),
    ]

def compile_data_export(data_type, data_sources, start_time=None, end_time=None, custom_parameters=None): # pylint: disable=too-many-locals, unused-argument, too-many-branches, too-many-statements
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

    if data_type == 'enrollment.scheduled_tasks':
        filename = tempfile.gettempdir() + os.path.sep + 'webmunk_scheduled_tasks.txt'

        with io.open(filename, 'w', encoding='utf-8') as outfile:
            writer = csv.writer(outfile, delimiter='\t')

            writer.writerow([
                'Identifier',
                'Task ID',
                'Task Name',
                'Active Date',
                'Completed Date',
                'Last Checked',
            ])

            for enrollment in Enrollment.objects.all():
                for task in enrollment.tasks.all().order_by('active'):
                    row = [
                        enrollment.assigned_identifier,
                        task.slug,
                        task.task,
                        task.active.astimezone(pytz.timezone(settings.TIME_ZONE)).isoformat(),
                    ]

                    if task.completed is not None:
                        row.append(task.completed.astimezone(pytz.timezone(settings.TIME_ZONE)).isoformat())
                    else:
                        row.append('')

                    if task.last_check is not None:
                        row.append(task.last_check.astimezone(pytz.timezone(settings.TIME_ZONE)).isoformat())
                    else:
                        row.append('')

                    writer.writerow(row)

        return filename

    if data_type == 'enrollment.enrollments':
        filename = tempfile.gettempdir() + os.path.sep + 'webmunk_enrollments.txt'

        with io.open(filename, 'w', encoding='utf-8') as outfile:
            writer = csv.writer(outfile, delimiter='\t')

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
                'Wishlist Install',
                'Wishlist Instructions',
                'Wishlist Uninstall',
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

                if task is None:
                    task = enrollment.tasks.filter(slug='main-survey-initial').exclude(completed=None).first()

                if task is not None:
                    enrollment_values.append(task.completed.astimezone(here_tz).strftime('%Y-%m-%d %H:%M'))
                else:
                    enrollment_values.append('')

                task = enrollment.tasks.filter(slug='upload-amazon-start').exclude(completed=None).first()

                if task is None:
                    task = enrollment.tasks.filter(slug='amazon-fetch-initial').exclude(completed=None).first()

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

                if task is None:
                    task = enrollment.tasks.filter(slug='amazon-fetch-final').exclude(completed=None).first()

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

                if task is None:
                    task = enrollment.tasks.filter(slug='main-survey-final').exclude(completed=None).first()

                if task is not None:
                    enrollment_values.append(task.completed.astimezone(here_tz).strftime('%Y-%m-%d %H:%M'))
                else:
                    enrollment_values.append('')

                task = enrollment.tasks.filter(slug='wishlist-initial').exclude(completed=None).first()

                if task is not None:
                    enrollment_values.append(task.completed.astimezone(here_tz).strftime('%Y-%m-%d %H:%M'))
                else:
                    enrollment_values.append('')

                task = enrollment.tasks.filter(slug='wishlist-task').exclude(completed=None).first()

                if task is not None:
                    enrollment_values.append(task.completed.astimezone(here_tz).strftime('%Y-%m-%d %H:%M'))
                else:
                    enrollment_values.append('')

                task = enrollment.tasks.filter(slug='wishlist-final').exclude(completed=None).first()

                if task is not None:
                    enrollment_values.append(task.completed.astimezone(here_tz).strftime('%Y-%m-%d %H:%M'))
                else:
                    enrollment_values.append('')

                # enrollment_values.append('-')

                writer.writerow(enrollment_values)

        return filename

    return None
