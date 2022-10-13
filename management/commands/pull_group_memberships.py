# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

from __future__ import print_function

from django.conf import settings
from django.core.management.base import BaseCommand

from quicksilver.decorators import handle_lock

from ...vendor.pdk_client import PDKClient

from ...models import Enrollment, EnrollmentGroup

class Command(BaseCommand):
    help = 'Pulls remote PDK group memberships into local enrollment server'

    @handle_lock
    def handle(self, *args, **options): # pylint: disable=too-many-locals, too-many-branches
        client = PDKClient(site_url=settings.PDK_API_URL, token=settings.PDK_API_TOKEN)

        query = client.query_data_sources(page_size=32)

        groups = {}

        for record in query:
            enrollments = Enrollment.objects.filter(assigned_identifier=record.get('identifier', None))

            group_name = record.get('group', None)

            if group_name is not None:
                group = groups.get(group_name, None)

                if group is None:
                    group = EnrollmentGroup.objects.filter(name=group_name).first()

                if group is None:
                    group = EnrollmentGroup.objects.create(name=group_name)

                if group is not None:
                    groups[group_name] = group

                    for enrollment in enrollments:
                        if enrollment.group is None or enrollment.group.pk != group.pk:
                            enrollment.group = group
                            enrollment.save()

                            print('Set %s group to %s' % (enrollment, group))
