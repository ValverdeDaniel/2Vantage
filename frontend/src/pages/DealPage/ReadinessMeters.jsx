// "Deal readiness" (A23; old CaseReadiness at 891f1b3): Intake, Proposal and Census, each a percent and its bar from
// the shell's `journey/` read (Hand-off is dropped with implementation). The colour bands are the old ones.

function readinessClass(pct) {
  if (pct >= 90) return 'bb-green';
  if (pct >= 70) return 'bb-amber';
  return 'bb-rose';
}

function Meter({ label, pct }) {
  return (
    <div className="bnf-meter">
      <div className="bnf-meter-head">
        <span className="bnf-meter-label">{label}</span>
        <span className={`bnf-meter-pct bb-mono ${readinessClass(pct)}`}>{pct}%</span>
      </div>
      <div className="bb-readiness-track">
        <div className={`bb-readiness-fill ${readinessClass(pct)}-bg`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

const NAMES = { intake: 'Intake', proposal: 'Proposal', census: 'Census' };

/** The meters under `label`, in `order`. The client page's Plan year block shows the same three as "This year at a
 *  glance", Intake, Census and Proposal (plan.md §8.5; slice 67). */
export default function ReadinessMeters({ meters, label = 'Deal readiness', order = ['intake', 'proposal', 'census'] }) {
  if (!meters) return null;
  return (
    <div className="bb-readiness bnf-readiness">
      <div className="bb-readiness-label">{label}</div>
      {order.map((key) => (
        <Meter key={key} label={NAMES[key]} pct={meters[key]} />
      ))}
    </div>
  );
}
