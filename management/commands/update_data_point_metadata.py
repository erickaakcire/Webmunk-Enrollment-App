# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

import json

from django.conf import settings
from django.core.management.base import BaseCommand

from quicksilver.decorators import handle_lock, handle_schedule, add_qs_arguments

from ...vendor.pdk_client import PDKClient

from ...models import Enrollment

class Command(BaseCommand):
    help = 'Adds relevent data point metadata to enrollments.'

    @add_qs_arguments
    def add_arguments(self, parser):
        pass

    @handle_lock
    @handle_schedule
    def handle(self, *args, **options): # pylint: disable=too-many-locals, too-many-branches
        client = PDKClient(site_url=settings.PDK_API_URL, token=settings.PDK_API_TOKEN)

        for enrollment in Enrollment.objects.all():
            metadata = json.loads(enrollment.metadata)

            query = client.query_data_points(page_size=32)

            last_point = query.filter(source=enrollment.assigned_identifier).order_by('-created').first()

            if last_point is not None:
                created = last_point.get('passive-data-metadata', {}).get('pdk_server_created', None)

                if created is not None:
                    metadata['latest_data_point'] = created

                    enrollment.metadata = json.dumps(metadata, indent=2)
                    enrollment.save()
