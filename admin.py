# pylint: disable=no-member, line-too-long

from django.contrib.gis import admin
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import Enrollment, ExtensionRuleSet, ScheduledTask, RuleMatchCount, PageContent

@admin.register(Enrollment)
class EnrollmentAdmin(admin.OSMGeoAdmin):
    list_display = ('assigned_identifier', 'enrolled', 'rule_set', 'last_fetched')
    list_filter = ('enrolled', 'last_fetched', 'rule_set', )

    search_fields = ('assigned_identifier',)

@admin.register(ExtensionRuleSet)
class ExtensionRuleSetAdmin(admin.OSMGeoAdmin):
    list_display = ('name', 'is_active', 'is_default',)
    list_filter = ('is_active', 'is_default',)

    search_fields = ('name', 'rule_json')

def reset_scheduled_task_completions(modeladmin, request, queryset): # pylint: disable=unused-argument, invalid-name
    queryset.update(completed=None)

reset_scheduled_task_completions.description = 'Reset scheduled task completions'

@admin.register(ScheduledTask)
class ScheduledTaskAdmin(admin.OSMGeoAdmin):
    list_display = ('enrollment', 'slug', 'task', 'active', 'last_check', 'completed')
    list_filter = ('active', 'completed', 'last_check', 'slug',)

    search_fields = ('task', 'slug', 'url',)
    actions = [reset_scheduled_task_completions]

@admin.register(RuleMatchCount)
class RuleMatchCountAdmin(admin.OSMGeoAdmin):
    list_display = ('url', 'pattern', 'matches', 'checked', 'content_length',)
    list_filter = ('checked', 'url', 'pattern',)
    readonly_fields = ['page_content',]

    search_fields = ('url', 'pattern',)

@admin.register(PageContent)
class PageContentAdmin(admin.OSMGeoAdmin):
    list_display = ('url', 'retrieved',)
    list_filter = ('retrieved', 'url')

    search_fields = ('url', 'content',)

    readonly_fields = ['rule_match_links',]

    def rule_match_links(self, obj): # pylint: disable=no-self-use
        links = []

        for link in obj.rule_matches.all().order_by('checked'):
            links.append('<a href="%s">%s</a>' % (reverse('admin:%s_%s_change' % ('enrollment', 'rulematchcount'), args=[link.id]), link))

        return mark_safe('<br />'.join(links)) # nosec

    rule_match_links.short_description = 'Rule matches'
