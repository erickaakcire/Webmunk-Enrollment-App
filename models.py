# pylint: disable=line-too-long, no-member

import base64
import json
import random

from nacl.secret import SecretBox
from six import python_2_unicode_compatible

from django.conf import settings
from django.contrib.gis.db import models
from django.utils import timezone
from django.utils.encoding import smart_str

def decrypt_value(stored_text):
    try:
        key = base64.b64decode(settings.ENROLLMENT_SECRET_KEY) # getpass.getpass('Enter secret backup key: ')

        box = SecretBox(key)

        ciphertext = base64.b64decode(stored_text.replace('secret:', '', 1))

        cleartext = box.decrypt(ciphertext)

        return smart_str(cleartext)

    except AttributeError:
        pass

    return None

def encrypt_value(cleartext):
    try:
        key = base64.b64decode(settings.ENROLLMENT_SECRET_KEY) # getpass.getpass('Enter secret backup key: ')

        box = SecretBox(key)

        uft8_bytes = cleartext.encode('utf-8')

        ciphertext = box.encrypt(uft8_bytes)

        return 'secret:' + smart_str(base64.b64encode(ciphertext))

    except AttributeError:
        pass

    return None

def generate_unique_identifier():
    identifier = None

    while identifier is None:
        try:
            identifier = settings.ENROLLMENT_GENERATE_IDENTIFIER()
        except AttributeError:
            identifier = str(random.randint(1, 99999999)) # nosec

            identifier = identifier.zfill(8)

        if Enrollment.objects.filter(assigned_identifier=identifier).count() > 0:
            identifier = None

    return identifier

@python_2_unicode_compatible
class ExtensionRuleSet(models.Model):
    name = models.CharField(max_length=1024)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    rule_json = models.TextField(max_length=(16 * 1024 * 1024), default='[]')

    def __str__(self):
        return str(self.name)

    def rules(self):
        return json.loads(self.rule_json)


@python_2_unicode_compatible
class Enrollment(models.Model):
    assigned_identifier = models.CharField(max_length=(4 * 1024), default='changeme')
    raw_identifier = models.CharField(max_length=(4 * 1024), default='changeme')

    enrolled = models.DateTimeField()
    last_fetched = models.DateTimeField()

    rule_set = models.ForeignKey(ExtensionRuleSet, related_name='enrollments', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return str(self.assigned_identifier)

    def assign_random_identifier(self, raw_identifier):
        if raw_identifier == self.current_raw_identifier():
            return # Same as current - don't add

        if hasattr(settings, 'ENROLLMENT_SECRET_KEY'):
            encrypted_identifier = encrypt_value(raw_identifier)

            self.raw_identifier = encrypted_identifier
        else:
            self.raw_identifier = raw_identifier

        if self.assigned_identifier == 'changeme' or self.assigned_identifier is None:
            self.assigned_identifier = generate_unique_identifier()

        self.save()

    def current_raw_identifier(self):
        if self.raw_identifier is not None and self.raw_identifier.startswith('secret:'):
            return decrypt_value(self.raw_identifier)

        return self.raw_identifier

@python_2_unicode_compatible
class ScheduledTask(models.Model):
    enrollment = models.ForeignKey(Enrollment, related_name='tasks', on_delete=models.CASCADE)

    active = models.DateTimeField()

    task = models.CharField(max_length=1024)
    slug = models.SlugField(max_length=1024)
    url = models.URLField(max_length=1024)

    last_check = models.DateTimeField(null=True, blank=True)
    completed = models.DateTimeField(null=True, blank=True)

    def is_complete(self):
        now = timezone.now()

        if self.active > now:
            return False

        if self.completed is not None:
            return True

        self.last_check = now
        self.save()

        try:
            if settings.WEBMUNK_CHECK_TASK_COMPLETE(self):
                self.completed = now
                self.save()

                return True
        except AttributeError:
            pass

        return False
