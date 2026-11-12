# Slice 25 (plan.md §6.11; J.6.2): `ProposalConfig` reshaped. v1.1's columns fold into one `config` merged by path
# (`notes` becomes `intro`; `lines`, the old membership, is dropped: `presented()` decides what prints, F119), and the
# builder's card marks get their own column. The old columns go in 0003, in a transaction of their own (Postgres
# refuses a schema change after data updates on a table with deferred foreign keys).

from django.db import migrations, models

LIMITS = {'title': 300, 'intro': 4000}


def forward(apps, schema_editor):
    ProposalConfig = apps.get_model('proposals', 'ProposalConfig')
    for row in ProposalConfig.objects.all():
        config = {}
        if (row.title or '').strip():
            config['title'] = row.title.strip()[: LIMITS['title']]
        if (row.notes or '').strip():
            config['intro'] = row.notes.strip()[: LIMITS['intro']]
        reasons = {
            str(line): str(text).strip()[:4000] for line, text in (row.reasons or {}).items() if str(text or '').strip()
        }
        if reasons:
            config['reasons'] = reasons
        if config:
            ProposalConfig.objects.filter(pk=row.pk).update(config=config)


class Migration(migrations.Migration):
    dependencies = [
        ('proposals', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='proposalconfig', name='config', field=models.JSONField(blank=True, default=dict)
        ),
        migrations.AddField(
            model_name='proposalconfig', name='marks', field=models.JSONField(blank=True, default=dict)
        ),
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
