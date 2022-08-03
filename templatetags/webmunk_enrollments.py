import pytz

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name='fetch_completed_task')
def fetch_completed_task(enrollment, slug):
    task = enrollment.tasks.filter(slug=slug).exclude(completed=None).first()

    if task is not None:
        here_tz = pytz.timezone(settings.TIME_ZONE)

        value = task.completed.astimezone(here_tz).strftime('%Y-%m-%d %H:%M')

        metadata = task.fetch_metadata()

        summary = metadata.get('summary', None)

        if summary is not None:
            value = value + '<br />' + summary

        return mark_safe(value) # nosec

    return ''
