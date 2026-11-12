# Slice 35 (plan.md §6.7; F78): whether a quote's rates already include the bundling discount.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quotes', '0005_saved_views'),
    ]

    operations = [
        migrations.AddField(
            model_name='plan',
            name='bundling',
            field=models.CharField(
                blank=True,
                choices=[
                    ('', 'Not confirmed'),
                    ('unbundled', 'Confirmed unbundled'),
                    ('included', 'Rates already include it'),
                ],
                default='',
                max_length=10,
            ),
        ),
    ]
