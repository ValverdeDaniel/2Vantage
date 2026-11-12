# Slice 25 (plan.md §6.11): v1.1's columns go once 0002 has copied them into `config`.

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('proposals', '0002_config_by_path'),
    ]

    operations = [
        migrations.RemoveField(model_name='proposalconfig', name='title'),
        migrations.RemoveField(model_name='proposalconfig', name='notes'),
        migrations.RemoveField(model_name='proposalconfig', name='lines'),
        migrations.RemoveField(model_name='proposalconfig', name='reasons'),
    ]
