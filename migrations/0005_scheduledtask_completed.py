# pylint: skip-file
# Generated by Django 3.2.12 on 2022-05-12 22:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('enrollment', '0004_scheduledtask'),
    ]

    operations = [
        migrations.AddField(
            model_name='scheduledtask',
            name='completed',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]