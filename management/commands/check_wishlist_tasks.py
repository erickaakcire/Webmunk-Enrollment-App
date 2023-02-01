# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

import datetime
import io
import json
import time
import zipfile

import arrow
import requests

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from quicksilver.decorators import handle_lock, handle_schedule, add_qs_arguments

from ...models import ScheduledTask, Enrollment
from ...vendor.pdk_client import PDKClient

class Command(BaseCommand):
    help = 'Verifies whether scheduled Qualtrics surveys have been completed and Webmunk is installed before creating wishlist tasks'

    @add_qs_arguments
    def add_arguments(self, parser):
        pass

    @handle_lock
    @handle_schedule
    def handle(self, *args, **options): # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        now = timezone.now()

        for survey_id in settings.WEBMUNK_QUALTRICS_WISHLIST_SURVEY_IDS:
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

                    print('STATUS: %s' % status)

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

                                            for survey_response in response_file.get('responses', []):
                                                if survey_response.get('values', {}).get('finished', 0) == 1:
                                                    webmunk_id = survey_response.get('values', {}).get('webmunk_id', None)

                                                    if webmunk_id is not None:
                                                        enrollment = Enrollment.objects.filter(assigned_identifier=webmunk_id).first()

                                                        if enrollment is not None:
                                                            # recorded = survey_response.get('values', {}).get('recordedDate', None)

                                                            metadata = enrollment.fetch_metadata()

                                                            if metadata.get('wishlist_enrolled', None) is None:
                                                                metadata['wishlist_enrolled'] = timezone.now().isoformat()
                                                                enrollment.metadata = json.dumps(metadata, indent=2)
                                                                enrollment.save()

                                                                print('WISHLIST ENROLLED: %s' % enrollment.assigned_identifier)
            else:
                print('START NON-200 HTTP CODE: %d -- %s: %s' % (response.status_code, start_url, response.text))

        only_before = arrow.get('2022-11-01T00:00:00+00:00') # Chiara picked this date!

        client = PDKClient(site_url=settings.PDK_API_URL, token=settings.PDK_API_TOKEN)

        for enrollment in Enrollment.objects.filter(enrolled__lte=only_before.datetime): # pylint: disable=too-many-nested-blocks
            metadata = enrollment.fetch_metadata()

            # 17724985
            # 19885339
            # 23989588
            # 45588624
            # 74858737
            # 82794101
            # 85514719
            # 88965052
            # 92246528
            # 95932274
            # 97273621

            #  "wishlist_ineligible": true,

            if metadata.get('wishlist_ineligible', False) is False:
                if metadata.get('wishlist_enrolled', None) is not None:
                    if ScheduledTask.objects.filter(enrollment=enrollment, slug='wishlist-task').count() == 0:
                        query = client.query_data_points(page_size=32)

                        last_point = query.filter(source=enrollment.assigned_identifier).order_by('-created').first()

                        if last_point is not None:
                            last_created = arrow.get(last_point.get('passive-data-metadata', {}).get('pdk_server_created', None))

                            enrollment_date = arrow.get(metadata['wishlist_enrolled']).datetime - datetime.timedelta(days=1)

                            if last_created is not None and last_created > enrollment_date:
                                final_url = 'https://hbs.qualtrics.com/jfe/form/SV_7UHQvvbYqJwMVVA?webmunk_id=%s' % enrollment.assigned_identifier

                                ScheduledTask.objects.create(enrollment=enrollment, active=now, task='Complete survey (please make sure you have 30 minutes to complete it)', slug='wishlist-task', url=final_url)

                    elif enrollment.tasks.filter(slug='wishlist-task').exclude(completed=None).count() > 0: # Completed second survey
                        if enrollment.tasks.filter(slug='wishlist-final').count() == 0:
                            data_points_uploaded = metadata.get('data_point_count', 0)
                            data_points_remaining = metadata.get('latest_pending_points_count', 0)

                            if data_points_remaining <= 10 and data_points_uploaded > 1000:
                                final_url = 'https://hbs.qualtrics.com/jfe/form/SV_414TKWcwjHxz6US?webmunk_id=%s' % enrollment.assigned_identifier

                                ScheduledTask.objects.create(enrollment=enrollment, active=timezone.now(), task='Uninstall Webmunk', slug='wishlist-final', url=final_url)
