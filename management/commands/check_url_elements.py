# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long, unexpected-keyword-arg

import base64
import json
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from quicksilver.decorators import handle_lock, handle_schedule, add_qs_arguments

from ...models import ExtensionRuleSet, RuleMatchCount, PageContent

class Command(BaseCommand):
    help = 'Checks outstanding tasks for completion'

    @add_qs_arguments
    def add_arguments(self, parser):
        pass

    @handle_lock
    @handle_schedule
    def handle(self, *args, **options): # pylint: disable=too-many-locals
        options = Options()
        options.add_argument('-headless')

        for url in settings.WEBMUNK_MONTIORING_URLS:
            chrome_options = Options()
            chrome_options.add_argument("--headless")

            capabilities = webdriver.DesiredCapabilities.CHROME.copy()
            capabilities['goog:loggingPrefs'] = { 'browser':'ALL' }

            driver = webdriver.Chrome(options=chrome_options, desired_capabilities=capabilities)

            driver.get(url)

            time.sleep(10)

            with open('/var/www/django/enroll.webmunk.org/webmunk_enrollment/enrollment/static/enrollment/jquery.js', 'r', encoding='utf-8') as jquery_script:
                script = jquery_script.read()

                driver.execute_script(script)

            with open('/var/www/django/enroll.webmunk.org/webmunk_enrollment/enrollment/static/enrollment/selenium-content-script.js', 'r', encoding='utf-8') as content_script:
                script = content_script.read()

                matches = []

                for rule_set in ExtensionRuleSet.objects.filter(is_active=True):
                    payload = {
                        'rules': rule_set.rules()
                    }

                    settings.WEBMUNK_UPDATE_ALL_RULE_SETS(payload)

                    rules = payload.get('rules', {}).get('rules', [])

                    for rule in rules:
                        rule_match = rule.get('match', None)

                        if rule_match is not None and (rule_match in matches) is False:
                            matches.append(rule_match)

                load_rules = 'window.webmunkRuleMatches = %s' % json.dumps(matches)

                driver.execute_script(load_rules)

                driver.execute_script(script)

                html_content = driver.execute_script("return document.documentElement.outerHTML;")

                now = timezone.now().replace(microsecond=0, second=0)

                page_content = PageContent.objects.create(url=url, retrieved=now, content=html_content)

                for entry in driver.get_log('browser'):
                    if 'WEBMUNK-JSON:' in entry.get('message', ''):
                        tokens = entry['message'].split('WEBMUNK-JSON:')

                        raw_json = base64.b64decode(tokens[1]).decode('utf-8')

                        counts = json.loads(raw_json)

                        # print('[console.log.count] %s' % json.dumps(counts, indent=2))

                        for pattern in counts.keys():
                            RuleMatchCount.objects.create(url=url, pattern=pattern, matches=counts[pattern], checked=now, page_content=page_content)

            driver.quit()
