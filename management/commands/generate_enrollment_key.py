# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

from __future__ import print_function

import base64

import nacl.secret
import nacl.utils

from django.core.management.base import BaseCommand
from django.utils.encoding import smart_str

class Command(BaseCommand):
    help = 'Generates a NaCl keypair for use with shared key encryption.'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options): # pylint: disable=too-many-locals,too-many-branches,too-many-statements
        key = nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)

        print('KEY: ' + smart_str(base64.b64encode(key)))
