# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

import json

import arrow

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
        for url in settings.PDK_API_URLS:
            client = PDKClient(site_url=url, token=settings.PDK_API_TOKEN)

            for enrollment in Enrollment.objects.all().order_by('assigned_identifier'):
                metadata = json.loads(enrollment.metadata)

                last_latest = arrow.get(metadata.get('latest_data_point', 0)).datetime

                query = client.query_data_points(page_size=1)

                last_points = query.filter(source=enrollment.assigned_identifier, created__gt=last_latest)

                last_point = last_points.order_by('-created').first()

                if last_point is not None:
                    created = last_point.get('passive-data-metadata', {}).get('pdk_server_created', None)

                    if created is not None:
                        metadata['latest_data_point'] = created

                        point_count = query.filter(source=enrollment.assigned_identifier).count()

                        metadata['data_point_count'] = point_count
                        metadata['data_point_server'] = url

                        print('%s - %s (%s)' % (enrollment.assigned_identifier, point_count, url,))

                        enrollment.metadata = json.dumps(metadata, indent=2)
                        enrollment.save()
