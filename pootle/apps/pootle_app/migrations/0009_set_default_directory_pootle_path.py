# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pootle_app', '0008_allow_blank_directory_name_and_parent'),
    ]

    operations = [
        migrations.AlterField(
            model_name='directory',
            name='pootle_path',
            field=models.CharField(default=b'/', unique=True, max_length=191, db_index=True),
        ),
    ]
