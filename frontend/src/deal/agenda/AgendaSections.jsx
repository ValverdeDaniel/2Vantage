import { useEffect, useRef, useState } from 'react';
import AgendaRow from './AgendaRow';
import { FollowUpForm, LaterForm } from './AgendaForms';
import { sectionsOf } from './rowView';
import TaskForm from './TaskForm';

/*
 * One deal's Agenda sections (I4–I7): Up next, Waiting on, Later, Blocked and Done, each with its ▾/▸ toggle, count and
 * one-line description; Done starts collapsed and an empty collapsed section is hidden (I5). `focus` (`?focus=task:12`
 * or a step id) scrolls to its row and flashes it for 2.2 s (I7). Old Vantage 891f1b3 `DealAgendaSections`.
 */
export default function AgendaSections({ payload, meta, focus, actions }) {
  const sections = sectionsOf(payload, meta);
  const focusSection = (payload?.rows || []).find((entry) => entry.id === focus)?.section;
  const [open, setOpen] = useState(() => {
    const shown = sections.map((section) => section.key).filter((key) => !isCollapsed(meta, key));
    return new Set(focusSection ? [...shown, focusSection] : shown);
  });
  const refs = useRef({});
  const [flashKey, setFlashKey] = useState(null);

  useEffect(() => {
    if (!focus || !focusSection) return undefined;
    const start = setTimeout(() => {
      setOpen((now) => new Set([...now, focusSection]));
      setFlashKey(focus);
    }, 0);
    const scroll = setTimeout(() => refs.current[focus]?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 60);
    const done = setTimeout(() => setFlashKey(null), 2200);
    return () => {
      clearTimeout(start);
      clearTimeout(scroll);
      clearTimeout(done);
    };
  }, [focus, focusSection]);

  function formFor(row) {
    const form = actions.form;
    if (!form || form.rowId !== row.id) return null;
    const busy = actions.busy === row.id;
    const cancel = () => actions.setForm(null);
    if (form.type === 'later') {
      return (
        <LaterForm
          meta={meta}
          today={payload.today}
          max={row.later_max}
          busy={busy}
          onCancel={cancel}
          onSave={(until, note) => actions.later(row, until, note)}
        />
      );
    }
    if (form.type === 'follow_up') {
      return (
        <FollowUpForm meta={meta} busy={busy} onCancel={cancel} onSave={(body, kind) => actions.followUp(row, body, kind)} />
      );
    }
    return (
      <TaskForm
        today={payload.today}
        task={row}
        busy={busy}
        onCancel={cancel}
        onSave={(changes) => actions.editTask(row, changes)}
      />
    );
  }

  const toggle = (key) =>
    setOpen((now) => {
      const next = new Set(now);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  return sections.map((section) => {
    const isOpen = open.has(section.key);
    if (!isOpen && section.rows.length === 0) return null;
    return (
      <div key={section.key} className="bnf-ag-block">
        <div className="bnf-ag-section">
          <div className="bnf-ag-section-head">
            <button type="button" className="bnf-ag-toggle" onClick={() => toggle(section.key)} aria-expanded={isOpen}>
              {isOpen ? '▾' : '▸'} {section.title} <span className="bnf-ag-count">{section.rows.length}</span>
            </button>
            {isOpen && section.sub && <span className="bnf-ag-section-sub">{section.sub}</span>}
          </div>
          {isOpen && section.rows.length === 0 && section.empty && <div className="bnf-ag-empty">{section.empty}</div>}
          {isOpen &&
            section.rows.map((row) => (
              <AgendaRow
                key={row.id}
                row={row}
                meta={meta}
                flash={flashKey === row.id}
                rowRef={(el) => {
                  if (el) refs.current[row.id] = el;
                }}
                busy={actions.busy === row.id}
                onAction={actions.act}
                form={formFor(row)}
              />
            ))}
        </div>
      </div>
    );
  });
}

function isCollapsed(meta, key) {
  return (meta?.agenda?.collapsed || []).includes(key);
}
