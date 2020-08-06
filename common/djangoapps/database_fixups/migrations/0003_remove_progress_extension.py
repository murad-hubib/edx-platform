# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

"""
The `progress-edx-platform-extensions` has been deprecated in favor of `edx-completion`.

The requirement was removed in the commit linked as (1) below. However its migration (2) had not been reverted.
That migration used `auth_user.id` as the foreign key in its models (3), but Django does not resolve this constraint
between existing tables anymore, because the model has been removed.
Therefore we need to drop the tables related to deprecated application in order to be able to remove users properly.

(1) https://github.com/edx-solutions/edx-platform/commit/59bf3efe71533de53b60bd979517e889d18a96bb
(2) https://github.com/edx-solutions/progress-edx-platform-extensions/blob/master/progress/migrations/0001_initial.py
(3) https://github.com/edx-solutions/progress-edx-platform-extensions/blob/master/progress/models.py
"""

class Migration(migrations.Migration):

    dependencies = [
        ('database_fixups', '0002_remove_foreign_keys_from_progress_extensions'),
    ]

    operations = [
        migrations.RunSQL('DROP TABLE IF EXISTS '
                          'progress_coursemodulecompletion, progress_studentprogress, progress_studentprogresshistory')
    ]
