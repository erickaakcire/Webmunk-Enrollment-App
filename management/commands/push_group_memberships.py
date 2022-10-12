# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

from __future__ import print_function

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

        for enrollment in Enrollment.objects.all().order_by('assigned_identifier'):
            local_group = None

            if enrollment.group is not None:
                local_group = enrollment.group.name

            query = client.query_data_sources(page_size=32).filter(identifier=enrollment.assigned_identifier)

            for item in query:
                remote_group = item.get('group', None)

                if local_group != remote_group:
                    group_update = client.update_data_sources().filter(identifier=enrollment.assigned_identifier)

                    update_count = group_update.update(group=local_group)

                    print('Updated %s with group %s: %d' % (enrollment, local_group, update_count))
