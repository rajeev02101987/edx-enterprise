# -*- coding: utf-8 -*-
# Generated by Django 1.11.27 on 2020-03-12 21:50
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('enterprise', '0091_add_sales_force_id_in_pendingenrollment'),
    ]

    operations = [
        migrations.AddField(
            model_name='enterprisecustomer',
            name='enable_portal_subscription_management_screen',
            field=models.BooleanField(default=False, help_text='Specifies whether to allow access to the subscription management screen in the admin portal.'),
        ),
        migrations.AddField(
            model_name='historicalenterprisecustomer',
            name='enable_portal_subscription_management_screen',
            field=models.BooleanField(default=False, help_text='Specifies whether to allow access to the subscription management screen in the admin portal.'),
        ),
    ]
