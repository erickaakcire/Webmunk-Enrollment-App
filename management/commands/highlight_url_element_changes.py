# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

import json
import statistics

from django.conf import settings
from django.core.management.base import BaseCommand

from quicksilver.decorators import handle_lock, handle_schedule, add_qs_arguments

from ...models import RuleMatchCount

class Command(BaseCommand):
    help = 'Checks outstanding tasks for completion'

    @add_qs_arguments
    def add_arguments(self, parser):
        pass

    @handle_lock
    @handle_schedule
    def handle(self, *args, **options): # pylint: disable=too-many-locals
        results = []

        patterns = RuleMatchCount.objects.order_by('pattern').values_list('pattern', flat=True).distinct()

        for url in settings.WEBMUNK_MONTIORING_URLS:
            for pattern in patterns:
                rule_matches = RuleMatchCount.objects.filter(url=url, pattern=pattern, matches__gt=0).order_by('checked')

                counts = []

                for rule_match in rule_matches:
                    counts.append(rule_match.matches)

                if len(counts) > 0 and sum(counts) > 0:
                    mean = statistics.mean(counts)
                    median = statistics.median(counts)
                    stdev = -1
                    normalized_stdev = -1

                    min_value = min(counts)
                    max_value = max(counts)

                    if len(counts) > 1:
                        stdev = statistics.stdev(counts)
                        normalized_stdev = stdev / max_value

                    latest = counts[-1]

                    results.append({
                        'url': url,
                        'pattern': pattern,
                        'latest': latest,
                        'min': min_value,
                        'max': max_value,
                        'mean': mean,
                        'median': median,
                        'stdev': stdev,
                        'normalized_stdev': normalized_stdev,
                        'observed': len(counts),
                    })

        results.sort(key=lambda result: result['normalized_stdev'], reverse=True)

        print(json.dumps(results, indent=2))
