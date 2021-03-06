# -*- coding: utf-8 -*-
# Generated by Django 1.11.27 on 2020-01-28 17:26
from __future__ import unicode_literals

from django.db import migrations, models

import enterprise.validators


class Migration(migrations.Migration):

    dependencies = [
        ('enterprise', '0085_enterprisecustomeruser_linked'),
    ]

    operations = [
        migrations.AddField(
            model_name='enterprisecustomer',
            name='contact_email',
            field=models.EmailField(blank=True, help_text='Email to be displayed as public point of contact for enterprise.', max_length=254, null=True),
        ),
        migrations.AddField(
            model_name='enterprisecustomerbrandingconfiguration',
            name='banner_background_color',
            field=models.CharField(blank=True, max_length=7, null=True, validators=[enterprise.validators.validate_hex_color]),
        ),
        migrations.AddField(
            model_name='enterprisecustomerbrandingconfiguration',
            name='banner_border_color',
            field=models.CharField(blank=True, max_length=7, null=True, validators=[enterprise.validators.validate_hex_color]),
        ),
        migrations.AddField(
            model_name='historicalenterprisecustomer',
            name='contact_email',
            field=models.EmailField(blank=True, help_text='Email to be displayed as public point of contact for enterprise.', max_length=254, null=True),
        ),
    ]
