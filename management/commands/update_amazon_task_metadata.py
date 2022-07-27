# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

import json

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

        for task in amazon_tasks:
            metadata = json.loads(task.metadata)

            if options.get('force', False) or ('item_count' in metadata) is False:
                query = client.query_data_points(page_size=32)

                item_count = -1

                if task.slug == 'upload-amazon-start':
                    item_count = query.filter(generator_identifier='pdk-external-amazon-item', source=task.enrollment.assigned_identifier, created__lte=task.enrollment.enrolled).count()
                else:
                    item_count = query.filter(generator_identifier='pdk-external-amazon-item', source=task.enrollment.assigned_identifier, created__gte=task.enrollment.enrolled).count()

                if item_count >= 0:
                    metadata['item_count'] = item_count

                    metadata['summary'] = '%d item(s)' % item_count

                    task.metadata = json.dumps(metadata, indent=2)
                    task.save()
