# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

import datetime
import json

import arrow
import requests

from django.conf import settings
from django.core.management.base import BaseCommand

from quicksilver.decorators import handle_lock, handle_schedule, add_qs_arguments

from ...models import ScheduledTask
from ...vendor.pdk_client import PDKClient

class Command(BaseCommand):
    help = 'Adds relevent metadata for Amazon tasks.'

    @add_qs_arguments
    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true')

    @handle_lock
    @handle_schedule
    def handle(self, *args, **options): # pylint: disable=too-many-locals, too-many-branches
        amazon_tasks = ScheduledTask.objects.exclude(completed=None).filter(slug__icontains='amazon')

        client = PDKClient(site_url=settings.PDK_API_URL, token=settings.PDK_API_TOKEN)

        for task in amazon_tasks: # pylint: disable=too-many-nested-blocks
            metadata = json.loads(task.metadata)

            if options.get('force', False) or ('item_count' in metadata) is False:
                query = client.query_data_points(page_size=32)

                item_count = -1

                amazon_items = []

                if task.slug == 'upload-amazon-start':
                    amazon_items = query.filter(generator_identifier='pdk-external-amazon-item', source=task.enrollment.assigned_identifier, created__lte=task.enrollment.enrolled)
                    item_count = amazon_items.count()
                else:
                    amazon_items = query.filter(generator_identifier='pdk-external-amazon-item', source=task.enrollment.assigned_identifier, created__gte=task.enrollment.enrolled).order_by('-recorded')
                    item_count = amazon_items.count()

                metadata['item_count'] = item_count
                metadata['summary'] = '%d item(s)' % item_count

                if item_count > 0:
                    pdk_ed_url  = 'https://pilot.webmunk.org/data/external/uploads/%s.json' % task.enrollment.assigned_identifier

                    amazon_divider = task.enrollment.enrolled + datetime.timedelta(days=settings.WEBMUNK_DATA_FOLLOWUP_DAYS)

                    try:
                        response = requests.get(pdk_ed_url, timeout=300)

                        if response.status_code == 200:
                            uploaded_items = response.json()

                            for item in uploaded_items:
                                if item['source'] == 'amazon':
                                    item_upload = arrow.get(item['uploaded']).datetime

                                    if task.slug == 'upload-amazon-start' and item_upload < amazon_divider:
                                        task.completed = item_upload
                                        break

                                    if task.slug == 'upload-amazon-final' and item_upload > amazon_divider:
                                        task.completed = item_upload

                                        for amazon_task in amazon_tasks:
                                            if amazon_task.enrollment == task.enrollment and amazon_task.slug == 'upload-amazon-start' and amazon_task.completed is None:
                                                amazon_task.completed = item_upload
                                                amazon_task.save()

                                        break
                        else:
                            print('RESP[%s]: %s -- %d' % (task.enrollment.assigned_identifier, pdk_ed_url, response.status_code))
                    except requests.exceptions.ConnectionError:
                        print('RESP[%s]: %s -- Unable to connect' % (task.enrollment.assigned_identifier, pdk_ed_url))

                task.metadata = json.dumps(metadata, indent=2)
                task.save()
