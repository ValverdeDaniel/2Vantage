"""Issue's gate (plan.md §5.4, §7.12 "Issuing" step 1; J28, J.5 B36, J.6.4): what refuses an issue, each in its
sentence, read from the builder's own fact sheets (`builder.laid_lines`), so the builder's banner, its checks and
Issue never disagree.

- our recommendation on every line that needs one (`ready`: kept lines, lines with only current plans and lines with
  a sold plan never block; the old D-175 rule);
- at most 16 plans on a line (`presented.MAX_COLUMNS`; a client page holds no more), in the checks' own sentence;
- something on the proposal at all.
"""

from quotes import presented

from .. import builder, checks, ready

NOTHING = 'No plans on this proposal yet — add or star the plans to present first.'  # the files' own refusal


def blockers(deal):
    """[sentence] that refuse issuing `deal` now; [] when it may be issued. Reads only."""
    stored, stored_marks = builder.stored_rows(deal)
    _blocks, sheets, _entries = builder.laid_lines(deal, stored, stored_marks)
    gate = ready.ready(sheets)
    out = [gate['sentence']] if gate['sentence'] else []
    for sheet in sheets:
        if not sheet['off'] and sheet['presented'] > presented.MAX_COLUMNS:
            out.append(checks.oversize_sentence(sheet['label'], sheet['presented'], presented.MAX_COLUMNS))
    if not out and not gate['ok']:
        out.append(NOTHING)
    return out
