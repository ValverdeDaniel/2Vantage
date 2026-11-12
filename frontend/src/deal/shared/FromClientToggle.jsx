/*
 * "These came from the client" (plan.md §3.7; B10, C4; D-060), the old `reviewrequest/FromClientToggle.jsx`: while it
 * is on, each answer typed is saved as the client's, entered by you (origin `relay`). Off by default; the tab owns it,
 * so leaving the tab (or the roster's ✎ Edit) turns it off and a later edit never inherits it. Intake and the Census
 * roster mount it.
 */
export default function FromClientToggle({ checked, onChange }) {
  return (
    <label
      className={`rr-fromclient${checked ? ' rr-fromclient-on' : ''}`}
      title="Tick when you are typing in answers the client sent another way (an email, a call, a spreadsheet). They are saved as the client's, entered by you."
    >
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      These came from the client
    </label>
  );
}
