from django.db import migrations

# Slice 7 (plan.md §6.7, F43, F50): the data steps after 0003 adds O.2's Plan fields.
# - `sort_order` becomes one sequence per line. 2V numbered it per role; each (deal, line) is renumbered 0..n-1 in the
#   order 2V showed (current, renewal, alternate; then the old number, then id), so nothing jumps on screen.
#   `order.layout` then groups the quotes under the plans they replace.
# - A star records its reason (F50): stars made before this slice were all hand-picked.
ROLE_ORDER = {'current': 0, 'renewal': 1, 'alternate': 2}


def one_order_per_line(apps, schema_editor):
    Plan = apps.get_model('quotes', 'Plan')
    rows = Plan.objects.order_by('deal_id', 'line').values_list('id', 'deal_id', 'line', 'role', 'sort_order')
    by_line = {}
    for pid, deal_id, line, role, order in rows:
        by_line.setdefault((deal_id, line), []).append((ROLE_ORDER.get(role, 3), order, pid))
    changed = []
    for plans in by_line.values():
        for index, (_role, order, pid) in enumerate(sorted(plans)):
            if order != index:
                changed.append(Plan(id=pid, sort_order=index))
    Plan.objects.bulk_update(changed, ['sort_order'], batch_size=500)
    Plan.objects.filter(starred=True, star_reason='').update(star_reason='Hand-picked')


class Migration(migrations.Migration):

    dependencies = [
        ('quotes', '0003_plan_fields'),
    ]

    operations = [
        # Going back, the per-line numbers still order each role's plans as before.
        migrations.RunPython(one_order_per_line, migrations.RunPython.noop),
    ]
