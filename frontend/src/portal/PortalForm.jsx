import { BorBlock, ContactsBlock, CoverageBlock, LinesBlock } from './blocks';
import { CensusFileCard, DocumentSlots } from './FileSlots';
import FollowUps from './FollowUps';
import IntakeSection from './IntakeSection';
import PeopleSection from './PeopleSection';
import { liveRail, nothingAsked, plural } from './portalModel';
import SubmitBar, { SavedNote, ThankYou } from './SubmitBar';
import TodoRail from './TodoRail';
import usePortalWrites from './usePortalWrites';

/*
 * What a link asks, on one page (plan.md §8.20; L80–L98, L105). Ported from old Vantage 891f1b3
 * `BenefitsClientPortal.jsx`'s main branch: the to-do rail (a sticky left column, above the form on a phone), the
 * greeting card, the shared request card ("From your broker:", "This request also went to N colleagues"), the intake
 * questions and blocks, the people, the files, the follow-ups and questions (slice 56), the notes and the foot.
 * Questionnaires join with slice 58, the receipt with 59.
 *
 * page: the payload · token · readOnly (View as client) · onReload() · onChallenge() (the PIN again)
 */
function Greeting({ page, rail, short }) {
  const name = page.account_name;
  const left = rail.total - rail.done;
  const heading = page.checklist?.done > 0
    ? `Welcome back — ${plural(left, 'item')} left for ${name}`
    : page.intake ? `${name} — benefits intake` : `A few details to finish ${name}'s benefits setup`;
  const census = page.census_file ? ' and a copy of your employee census' : '';
  return (
    <div className="bb-portal-card">
      <div className="bb-eyebrow">Requested by {page.agency.name}</div>
      <div className="bb-portal-heading">{heading}</div>
      <div className="bb-portal-intro">
        Hi — your benefits team at {short} needs{' '}
        {rail.total > 0 ? `the ${plural(rail.total, 'item')} below` : 'a couple of things below'}
        {census}. You’ll only see what’s still needed — save your progress any time and submit when you’re done.
      </div>
    </div>
  );
}

function SharedCard({ page }) {
  if (!page.message && !page.colleagues && !page.answered_elsewhere_at) return null;
  return (
    <div className="bb-portal-card bnf-portal-shared">
      {page.message && (
        <div className="bnf-portal-shared-message">
          <b>From your broker:</b> {page.message}
        </div>
      )}
      {page.colleagues > 0 && (
        <div className="bb-panel-sub">
          This request also went to {plural(page.colleagues, 'colleague')} at your company — anything either of you
          enters saves to the same place.
        </div>
      )}
      {page.answered_elsewhere_at && (
        <div className="bb-panel-sub">
          A colleague sent this back on {new Date(page.answered_elsewhere_at).toLocaleDateString()} — you can still add
          or correct anything.
        </div>
      )}
    </div>
  );
}

export default function PortalForm({ token, page, readOnly = false, onReload, onChallenge }) {
  const writes = page.can_write && !readOnly;
  const w = usePortalWrites({ token, page, writes, onReload, onChallenge });
  const short = (page.agency.name || 'your broker').split(' ')[0];
  const rail = liveRail(page, w.answers.values, w.staged);
  const blocks = page.intake?.blocks || {};
  const files = { staged: w.staged, onStage: w.stage, onUnstage: w.unstage, onProblem: w.setProblem, readOnly: !writes };

  if (w.submitted && !readOnly) return <ThankYou short={short} />;
  if (nothingAsked(page)) {
    return (
      <div className="bb-portal-card bb-portal-center">
        <div className="bb-portal-thanks-title">Nothing is needed from you right now</div>
        <div className="bb-subtitle">
          Your benefits team at {short} has nothing open on this link. If that changes, it will show here.
        </div>
      </div>
    );
  }
  return (
    // min-width 0 on the grid's items: under 860 px the old sheet's single `1fr` column otherwise grows to its widest
    // form row and the page scrolls sideways on a phone (§8.20, usable at 390 px; slice 54).
    <div className="bnf-portal-grid">
      <aside className="bnf-portal-rail" style={{ minWidth: 0 }}>
        <TodoRail rail={rail} />
      </aside>
      <div className="bnf-portal-main" style={{ minWidth: 0 }}>
        <Greeting page={page} rail={rail} short={short} />
        <SharedCard page={page} />
        {(page.follow_ups || []).length > 0 && <FollowUps token={token} page={page} short={short} readOnly={!writes} />}
        <IntakeSection intake={page.intake} bind={w.bind} />
        {blocks.contacts && <ContactsBlock block={blocks.contacts} bind={w.bind} />}
        {blocks.coverage && <CoverageBlock block={blocks.coverage} bind={w.bind} />}
        {blocks.lines && <LinesBlock block={blocks.lines} bind={w.bind} />}
        {blocks.bor && <BorBlock bor={blocks.bor} name={w.borName} onName={w.setBorName} readOnly={!writes} />}
        <PeopleSection people={page.people} adder={writes ? page.add_people : null} bind={w.bind}
                       onAdd={w.addPerson} />
        <DocumentSlots documents={page.documents} {...files} />
        <CensusFileCard token={token} censusFile={page.census_file} canTemplate={!readOnly} {...files} />
        {!(page.follow_ups || []).length && <FollowUps token={token} page={page} short={short} readOnly={!writes} />}
        <SavedNote note={w.note} problem={w.problem} onRetry={writes ? w.save : null} busy={w.busy} />
        {!readOnly && (
          <SubmitBar
            agency={page.agency}
            accountName={page.account_name}
            short={short}
            open={rail.total - rail.done}
            confirming={w.confirming}
            busy={w.busy}
            disabled={!writes}
            onSave={w.save}
            onSubmit={() => w.submit(rail.total - rail.done)}
          />
        )}
      </div>
    </div>
  );
}
