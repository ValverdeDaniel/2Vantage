import { useState } from 'react';

const blankStat = { value: '', label: '', note: '' };
const blankRow = { meeting: '', topics: [], when: '' };

/*
 * What the firm says about itself on the Presentation format's pages (plan.md §8.14; J155; the old FirmPagesPanel's
 * "Who we are" and "How we work together through the year" at 891f1b3, same words and classes): its story and up to
 * six figures, and its meeting calendar (up to eight). Nothing here is ever filled in for the firm: an empty section
 * prints no page, and a figure is the firm's own claim to stand behind. Each part saves on leaving it (`onSave` with
 * the field that changed); rows with nothing typed are dropped by the server. The drawer remounts it after a load.
 */
export default function FirmStory({ pages, limits, onSave }) {
  const [about, setAbout] = useState(pages.about_text);
  const [stats, setStats] = useState(pages.about_stats);
  const [calendar, setCalendar] = useState(pages.service_calendar);
  const editStat = (index, change) => setStats((now) => now.map((row, i) => (i === index ? { ...row, ...change } : row)));
  const editRow = (index, change) => setCalendar((now) => now.map((row, i) => (i === index ? { ...row, ...change } : row)));
  return (
    <>
      <div className="bnf-present-block">
        <div className="bnf-present-head">Who we are</div>
        <textarea
          className="bnf-present-summary"
          rows={4}
          maxLength={limits.about}
          value={about}
          placeholder="Who the firm is and why a client should trust it, in two or three sentences."
          aria-label="Who we are"
          onChange={(event) => setAbout(event.target.value)}
          onBlur={() => about.trim() !== pages.about_text && onSave({ about_text: about })}
        />
        <div className="bnf-output-hint">Figures beside it, at most six. Use only numbers the firm can stand behind.</div>
        {stats.map((stat, index) => (
          // A row has no identity of its own until it is saved.
          <div key={index} className="bnf-present-year">
            <input
              type="text"
              maxLength={24}
              placeholder="Figure"
              aria-label="Figure"
              value={stat.value}
              onChange={(event) => editStat(index, { value: event.target.value })}
              onBlur={() => onSave({ about_stats: stats })}
            />
            <input
              type="text"
              className="bnf-present-wide"
              maxLength={80}
              placeholder="What it counts"
              aria-label="What it counts"
              value={stat.label}
              onChange={(event) => editStat(index, { label: event.target.value })}
              onBlur={() => onSave({ about_stats: stats })}
            />
            <button
              type="button"
              className="bnf-override-link"
              onClick={() => {
                const next = stats.filter((_row, i) => i !== index);
                setStats(next);
                onSave({ about_stats: next });
              }}
            >
              Remove
            </button>
          </div>
        ))}
        {stats.length < limits.stats && (
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => setStats((now) => [...now, blankStat])}>
            ＋ Add a figure
          </button>
        )}
      </div>
      <div className="bnf-present-block">
        <div className="bnf-present-head">How we work together through the year</div>
        {calendar.map((row, index) => (
          <div key={index} className="bnf-present-year">
            <input
              type="text"
              className="bnf-present-name"
              maxLength={80}
              placeholder="Meeting"
              aria-label="Meeting"
              value={row.meeting}
              onChange={(event) => editRow(index, { meeting: event.target.value })}
              onBlur={() => onSave({ service_calendar: calendar })}
            />
            <input
              type="text"
              className="bnf-present-wide"
              placeholder="What it covers, separated by semicolons"
              aria-label="What it covers, separated by semicolons"
              value={(row.topics || []).join('; ')}
              onChange={(event) => editRow(index, { topics: event.target.value.split(';').map((topic) => topic.trimStart()) })}
              onBlur={() => onSave({ service_calendar: calendar })}
            />
            <input
              type="text"
              maxLength={60}
              placeholder="When"
              aria-label="When"
              value={row.when}
              onChange={(event) => editRow(index, { when: event.target.value })}
              onBlur={() => onSave({ service_calendar: calendar })}
            />
            <button
              type="button"
              className="bnf-override-link"
              onClick={() => {
                const next = calendar.filter((_row, i) => i !== index);
                setCalendar(next);
                onSave({ service_calendar: next });
              }}
            >
              Remove
            </button>
          </div>
        ))}
        {calendar.length < limits.calendar && (
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => setCalendar((now) => [...now, blankRow])}>
            ＋ Add a meeting
          </button>
        )}
      </div>
    </>
  );
}
