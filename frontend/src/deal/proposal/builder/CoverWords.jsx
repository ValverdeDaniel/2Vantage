/*
 * The cover's title and introduction (plan.md §8.14; J34; the old CoverPicker's `bnf-build-words` at 891f1b3): each
 * saved on leaving it, when it changed (`title` ≤300, `intro` ≤4,000). A blank title prints the deal's own ("2027
 * Benefits Proposal"); the placeholder says what the old one said. Remounted when the saved words change.
 */
export default function CoverWords({ words, client, meta, busy, onSet }) {
  const save = (path, saved) => (event) => {
    const text = event.target.value.trim();
    if (text !== saved) onSet(path, text);
  };
  return (
    <div className="bnf-build-words">
      <label>
        <span>Title</span>
        <input
          key={`title-${words.title}`}
          type="text"
          maxLength={meta.limits.title}
          defaultValue={words.title}
          disabled={busy}
          placeholder={`${client || 'Client'} — Employee Benefits Proposal`}
          onBlur={save('title', words.title)}
        />
      </label>
      <label>
        <span>Introduction</span>
        <textarea
          key={`intro-${words.intro}`}
          rows={3}
          maxLength={meta.limits.text}
          defaultValue={words.intro}
          disabled={busy}
          placeholder="A few sentences to open the proposal."
          onBlur={save('intro', words.intro)}
        />
      </label>
    </div>
  );
}
