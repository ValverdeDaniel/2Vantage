"""The carrier-data generator (G124) on a small synthetic template with both of the real form's traps — a stale
`<variables>` block and dirty labels — and the start-up checks (G125). No database."""

import ast

import pytest

from questionnaire import checks
from questionnaire.forms import fl_blue_51_layout
from questionnaire.xfa.parse import parse_template
from questionnaire.xfa.render import render_data_module

TEMPLATE = """<template>
<variables><script>var stale = newArray("Heart&#160;Thing", "Dropped Long Ago");</script></variables>
<subform name="form">
 <field name="drpMedCat"><caption><value><text>Medical&#160;Category</text></value></caption><ui/>
  <items><text>Heart Things</text><text>Bone  Things </text></items>
  <items save="1"><text>Heart&#160;Things</text><text>Bone  Things </text></items>
 </field>
 <field name="drpMedCondition"><event activity="change"><script>
  txtSurgPlanned.presence = "hidden";
  switch (this.rawValue) {
   case "Heart Things":
     drpMedCondition.addItem("Murmur&#160; ");
     drpMedCondition.addItem("Bypass &amp; Repair");
     txtSurgPlanned.presence = "visible";
     break;
   case "Bone  Things ":
     drpMedCondition.addItem("Fracture");
     break;
  }
 </script></event></field>
 <field name="drpMedConDetail"><event activity="change"><script>
  numCancerDetailyes.presence = "hidden";
  switch (this.rawValue) {
   case "Murmur":
   case "Bypass &amp; Repair":
     drpMedConDetail.addItem("Mild");
     break;
  }
 </script></event></field>
 <field name="drpSIC"><items><text>0111</text><text>0112</text></items>
  <items save="1"><text>Wheat</text><text>Rice</text></items></field>
 <subform name="tblCategories"><subform layout="row"><draw><value><text>Heart&#160;Things</text></value></draw>
  </subform></subform>
</subform>
</template>"""


def test_G124_the_generator_reads_the_switch_bodies_never_the_stale_variables():
    parsed = parse_template(TEMPLATE.encode())
    assert parsed['MED_CATEGORIES'] == ['Heart Things', 'Bone Things']
    assert parsed['CONDITIONS_BY_CATEGORY'] == {
        'Heart Things': ['Murmur', 'Bypass & Repair'],
        'Bone Things': ['Fracture'],
    }
    assert 'Dropped Long Ago' not in str(parsed)
    assert parsed['DETAILS_BY_CONDITION'] == {'Murmur': ['Mild'], 'Bypass & Repair': ['Mild']}  # a fall-through run


def test_G124_dirty_labels_join_identically_on_both_levels():
    parsed = parse_template(TEMPLATE.encode())
    assert set(parsed['MED_CATEGORIES']) == set(parsed['CONDITIONS_BY_CATEGORY'])
    every_condition = {c for cs in parsed['CONDITIONS_BY_CATEGORY'].values() for c in cs}
    assert set(parsed['DETAILS_BY_CONDITION']) <= every_condition


def test_G124_effects_overrides_sic_legend_and_captions():
    parsed = parse_template(TEMPLATE.encode())
    assert (
        parsed['CATEGORY_EFFECTS']['Heart Things']['surgery']
        and not parsed['CATEGORY_EFFECTS']['Bone Things']['surgery']
    )
    assert parsed['CONDITION_OVERRIDES'] == ['cancer_counts']
    assert parsed['SIC_CODES'] == [('0111', 'Wheat'), ('0112', 'Rice')]
    assert parsed['CATEGORY_LEGEND'] == [['Heart Things']]
    assert parsed['CAPTIONS']['drpMedCat'] == 'Medical Category'


def test_G124_the_rendered_module_is_python_and_deterministic():
    parsed = parse_template(TEMPLATE.encode())
    text = render_data_module(parsed)
    assert text == render_data_module(parse_template(TEMPLATE.encode())) and '\r' not in text
    tree = ast.parse(text)
    names = {t.id for node in tree.body if isinstance(node, ast.Assign) for t in node.targets}
    assert {'SOURCE_SHA256', 'SIC_CODES', 'CONDITIONS_BY_CATEGORY'} <= names


def test_G124_a_template_without_the_cascade_is_refused():
    with pytest.raises(ValueError):
        parse_template(b'<template><field name="drpMedCat"><items save="1"><text>A</text></items></field></template>')


def test_G125_the_bundled_files_match_and_a_changed_blank_fails_the_check(monkeypatch):
    assert checks.problems() == []
    monkeypatch.setattr(fl_blue_51_layout, 'BLANK_SHA256', '0' * 64)
    assert any('measured on' in sentence for sentence in checks.problems())
