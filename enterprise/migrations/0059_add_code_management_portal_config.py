# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2018-12-14 17:46
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('enterprise', '0058_auto_20181212_0145'),
    ]

    operations = [
        migrations.AddField(
            model_name='enterprisecustomer',
            name='enable_portal_code_management_screen',
            field=models.BooleanField(default=False, help_text='Specifies whether to allow access to the code management screen in the admin portal.'),
        ),
        migrations.AddField(
            model_name='historicalenterprisecustomer',
            name='enable_portal_code_management_screen',
            field=models.BooleanField(default=False, help_text='Specifies whether to allow access to the code management screen in the admin portal.'),
        ),
    ]
