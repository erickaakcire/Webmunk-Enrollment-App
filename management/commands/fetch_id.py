# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

from django.core.management.base import BaseCommand

from ...models import Enrollment

class Command(BaseCommand):
    help = 'Retrieves assigned identifier from raw identifier'

    def add_arguments(self, parser):
        parser.add_argument('identifier', help='raw identifier')

    def handle(self, *args, **options): # pylint: disable=too-many-locals, too-many-branches
        raw_identifier = options.get('identifier', None)

        for enrollment in Enrollment.objects.all():
            if enrollment.current_raw_identifier() == raw_identifier:
                print('Found %s...' % enrollment.assigned_identifier)
