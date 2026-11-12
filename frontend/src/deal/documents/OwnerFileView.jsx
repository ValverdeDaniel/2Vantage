import { Link } from 'react-router';
import { RosterBeside } from '../census';
import IntakeFileView from './IntakeFileView';

/*
 * The Scanned data of a file whose values another tab owns (plan.md §8.16; E43–E45, D130; slice 65): a census file
 * opens beside the whole roster (OQ97's default), an intake file beside the intake form's answers, and a filled
 * questionnaire points to the Questionnaire tab, where its answers are read (E45). Other files say what the old
 * station said.
 */
export default function OwnerFileView({ deal, meta, scope, activeRef, onShow }) {
  if (scope.bucket === 'census') return <RosterBeside deal={deal} meta={meta} />;
  if (scope.bucket === 'intake') {
    return <IntakeFileView deal={deal} meta={meta} scope={scope} activeRef={activeRef} onShow={onShow} />;
  }
  if (scope.bucket === 'questionnaire') {
    return (
      <div className="bb-subtitle bb-mt" data-questionnaire-pointer>
        Filled questionnaires are read on the Questionnaire tab —{' '}
        <Link className="bnf-linklike" to={`/deals/${deal.id}/questionnaire`}>
          open the Questionnaire tab ▸
        </Link>
      </div>
    );
  }
  return (
    <div className="bb-subtitle bb-mt">
      Nothing is read from this file — assign and preview it here; any fields traced to it appear once available.
    </div>
  );
}
