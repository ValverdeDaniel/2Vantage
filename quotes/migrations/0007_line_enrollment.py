# Slice 13 (plan.md §5.5, §6.7; F88, F91, O.6 #10): one LineEnrollment per deal and line — the whole-line figure, the
# line's one switch and when its typed counts were saved. The plans' typed counts move under that switch: a line whose
# typed plans were all switched off keeps them, switched off; on a line with any switched on, a plan switched off was not
# pricing anyway, so its counts are cleared. `Plan.enrollment_on` goes in 0008.

import django.db.models.deletion
from django.db import migrations, models


def to_lines(apps, schema_editor):
    Plan = apps.get_model('quotes', 'Plan')
    LineEnrollment = apps.get_model('quotes', 'LineEnrollment')
    typed = {}
    for plan in Plan.objects.exclude(enrollment={}).only('id', 'deal_id', 'line', 'enrollment_on', 'updated_at'):
        typed.setdefault((plan.deal_id, plan.line), []).append(plan)
    for (deal_id, line), plans in typed.items():
        on = any(plan.enrollment_on for plan in plans)
        LineEnrollment.objects.create(
            deal_id=deal_id, line=line, on=on, typed_at=max(plan.updated_at for plan in plans)
        )
        if on:
            off = [plan.id for plan in plans if not plan.enrollment_on]
            Plan.objects.filter(id__in=off).update(enrollment={})


class Migration(migrations.Migration):

    dependencies = [
        ('deals', '0001_initial'),
        ('quotes', '0006_plan_bundling'),
    ]

    operations = [
        migrations.CreateModel(
            name='LineEnrollment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('line', models.CharField(max_length=20)),
                ('enrollment', models.JSONField(blank=True, default=dict)),
                ('on', models.BooleanField(default=True)),
                ('typed_at', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'deal',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='line_enrollments',
                        to='deals.deal',
                    ),
                ),
            ],
            options={
                'constraints': [
                    models.UniqueConstraint(fields=('deal', 'line'), name='one_line_enrollment_per_line')
                ],
            },
        ),
        migrations.RunPython(to_lines, migrations.RunPython.noop),
    ]
