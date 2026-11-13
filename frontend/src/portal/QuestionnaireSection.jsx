import PaperForm from '../deal/questionnaire/PaperForm';
import BlankForm from './BlankForm';
import ConflictNote from './ConflictNote';
import QuestionnairePaper from './QuestionnairePaper';
import QuestionnaireSign from './QuestionnaireSign';
import { formDraft, formRef, introWords, specOnScreen } from './questionnaireModel';
import useFormSpec from './useFormSpec';

/*
 * The carrier forms a link asks for, one card each in the request's order (plan.md §8.20; G83–G98, L91; slice 58).
 * Ported from old Vantage 891f1b3 `BenefitsClientPortal.jsx` (the questionnaire cards): the form's title and subtitle,
 * the official blank to view or download (G84), "Signed by … Thank you" or the intro, the form itself in the paper
 * layout the team uses (the shared PaperForm, G36; the server says what is on screen, G25), the broker's fields as
 * text (G86), the rows their link added with Remove (G87), "Already filled this out on paper?" (G90, G92) and the
 * officer's signature (G93). A form asked only as a signed copy shows the blank and the upload.
 *
 * w: usePortalWrites' answer (bind, answers, forms, files); token ('' in a preview); readOnly.
 */
function Foot({ card, slot, bind }) {
  const ref = formRef(card.form, slot);
  const colleague = card.state.colleague?.includes(slot);
  if (!bind.errors[ref] && !bind.conflicts[ref] && !colleague) return null;
  return (
    <>
      {colleague && <div className="bnf-portal-colleague">Updated by someone else on your team</div>}
      {bind.errors[ref] && <div className="bnf-issue-line bb-rose">{bind.errors[ref]}</div>}
      <ConflictNote conflict={bind.conflicts[ref]} onKeep={() => bind.keepTheirs(ref)} onMine={() => bind.useMine(ref)} />
    </>
  );
}

function OnlineForm({ token, card, state, w, readOnly }) {
  const spec = useFormSpec(token, { ...card, state });
  if (spec.isPending) return <div className="loading">Loading the form…</div>;
  if (spec.isError) return <div className="bnf-issue-line bb-rose">Could not load this form — please reload the page.</div>;
  const broker = new Set(state.broker || []);
  const locked = readOnly || card.locked || w.forms.busy === card.form;
  return (
    <PaperForm
      spec={specOnScreen(spec.data, state)}
      data={state}
      draft={formDraft(card.form, w.answers)}
      onChange={(slot, value) => w.bind.set(formRef(card.form, slot), value)}
      onAddRow={(block) => w.forms.addRow(card.form, block)}
      onRemoveRow={(block, rowId) => w.forms.removeRow(card.form, block, rowId)}
      disabled={locked}
      lockedOf={(slot) => broker.has(slot)}
      canRemove={(row) => Boolean(row.mine)}
      footOf={(slot) => <Foot card={{ ...card, state }} slot={slot} bind={w.bind} />}
    />
  );
}

function Card({ token, card, w, files, readOnly }) {
  const state = w.forms.states[card.form] || card.state;
  return (
    <div id={`bnf-sec-questionnaire_${card.form}`} className="bb-portal-card" data-ask-ref={`qform:${card.form}`}>
      <div className="bb-panel-title">{card.title}</div>
      <div className="bb-panel-sub">{card.subtitle}</div>
      {card.blank && <BlankForm token={token} form={card.form} onProblem={files.onProblem} />}
      {card.signed ? (
        <div className="bnf-esign-done">
          Signed by {card.signed.name}. Thank you — nothing further is needed on this form.
        </div>
      ) : (
        state && <p className="bnf-q-intro">{introWords(card)}</p>
      )}
      {state && <OnlineForm token={token} card={card} state={state} w={w} readOnly={readOnly} />}
      {card.file && !card.signed && <QuestionnairePaper file={card.file} copyOnly={card.mode === 'upload'} {...files} />}
      {card.sign && !readOnly && (
        <QuestionnaireSign
          sign={card.sign}
          name={w.forms.names[card.form]}
          onName={(name) => w.forms.setName(card.form, name)}
          hold={w.forms.holds[card.form]}
          anyway={w.forms.anyway[card.form]}
          onAnyway={(value) => w.forms.setAnyway(card.form, value)}
          readOnly={readOnly}
        />
      )}
    </div>
  );
}

export default function QuestionnaireSection({ token, cards, w, files, readOnly }) {
  return (cards || []).map((card) => (
    <Card key={card.form} token={token} card={card} w={w} files={files} readOnly={readOnly} />
  ));
}
