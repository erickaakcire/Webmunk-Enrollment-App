# pylint: disable=no-member, line-too-long

from django.contrib.gis import admin

from .models import Enrollment, ExtensionRuleSet

@admin.register(Enrollment)
class EnrollmentAdmin(admin.OSMGeoAdmin):
    list_display = ('assigned_identifier', 'enrolled', 'last_fetched')
    list_filter = ('enrolled', 'last_fetched')

    search_fields = ('assigned_identifier',)

@admin.register(ExtensionRuleSet)
class ExtensionRuleSetAdmin(admin.OSMGeoAdmin):
    list_display = ('name', 'is_active', 'is_default',)
    list_filter = ('is_active', 'is_default',)

    search_fields = ('name', 'rule_json')
