# Slice 13 (plan.md §6.7; F88, O.6 #10): `Plan.enrollment_on` goes; `LineEnrollment.on` is the line's one switch.
# Its own migration, after 0007's data step (Postgres refuses schema changes after data updates in one transaction).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('quotes', '0007_line_enrollment'),
    ]

    operations = [
        migrations.RemoveField(model_name='plan', name='enrollment_on'),
    ]
