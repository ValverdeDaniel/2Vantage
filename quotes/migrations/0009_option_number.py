# Slice 25 (plan.md §5.4, §6.7; J159, OQ35, OQ36): `Plan.option_number`, "Option n" per line, replaces v1.1's
# `option_label` (O.6 #15). Labels were never stamped (Issue had not been built), so nothing carries over.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quotes', '0008_drop_enrollment_on'),
    ]

    operations = [
        migrations.RemoveConstraint(model_name='plan', name='option_label_unique_per_deal'),
        migrations.RemoveField(model_name='plan', name='option_label'),
        migrations.AddField(
            model_name='plan',
            name='option_number',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name='plan',
            constraint=models.UniqueConstraint(
                condition=models.Q(('option_number__isnull', False)),
                fields=('deal', 'line', 'option_number'),
                name='option_number_unique_per_line',
            ),
        ),
    ]
