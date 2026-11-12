# Slice 13 follow-up (plan.md §5.5, §6.7; F91): `LineEnrollment.census_seen`, how many census imports the deal had
# applied when the line's typed counts were saved. "Typed before the latest import" compares this count with the
# deal's applied imports instead of two clock stamps, which a clock stepping back could put in the wrong order. Rows
# saved before it count the imports applied by their `typed_at`, which is what the stamps said until now.

from django.db import migrations, models


def seen(apps, schema_editor):
    LineEnrollment = apps.get_model('quotes', 'LineEnrollment')
    CensusImport = apps.get_model('census', 'CensusImport')
    for row in LineEnrollment.objects.exclude(typed_at=None):
        applied = CensusImport.objects.filter(deal_id=row.deal_id, status='applied', applied_at__lte=row.typed_at)
        LineEnrollment.objects.filter(pk=row.pk).update(census_seen=applied.count())


class Migration(migrations.Migration):
    dependencies = [
        ('census', '0001_initial'),
        ('quotes', '0009_option_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='lineenrollment',
            name='census_seen',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.RunPython(seen, migrations.RunPython.noop),
    ]
