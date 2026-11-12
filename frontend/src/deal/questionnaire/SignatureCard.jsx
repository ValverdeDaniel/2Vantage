import { useState } from 'react';
import { useSign } from '../../api/questionnaire';
import { errorStatus, errorText } from '../../lib/errors';
import ConfirmDialog from '../../ui/ConfirmDialog';
import { useToast } from '../../ui/useToast';

/*
 * The signatures (G49–G53; OQ54: typed names, plus the paper-copy route): the officer ("Plan sponsor — authorized
 * company officer" on the SIIA form) and the licensed agent, one typed-name box. Each signature is offered while it is
 * missing — the agent's after the lock too. Staff sign for the officer only with the officer's written authorization
 * ticked; the confirm says it attests to every answer and locks the form, and names answers still waiting for review.
 * Blank required answers hold the officer's signature until "Sign anyway" (the server's 409 names how many).
 */
export default function SignatureCard({ deal, spec, data, flush }) {
  const toast = useToast();
  const sign = useSign(deal.id, data.form);
  const [name, setName] = useState('');
  const [authorized, setAuthorized] = useState(false);
  const [ask, setAsk] = useState(null); // {who, anyway, message}
  const typed = name.trim();
  const waiting = (data.waiting || 0) + Object.values(data.status || {}).filter((s) => s === 'to_check').length;

  function confirmWords(who) {
    const warn = waiting ? `${waiting} answer${waiting === 1 ? ' is' : 's are'} still to review. ` : '';
    if (who === 'officer') return `${warn}Signing for the company officer as “${typed}” attests to every answer on the form and locks it.`;
    return `${warn}Sign as the agent, “${typed}”?`;
  }

  async function run(who, anyway = false) {
    await flush();
    sign.mutate(
      { who, name: typed, authorized: who === 'officer' && authorized, sign_anyway: anyway },
      {
        onSuccess: () => {
          setAsk(null);
          setName('');
          setAuthorized(false);
          toast.success('Signature recorded');
        },
        onError: (error) => {
          const body = error.response?.data || {};
          if (errorStatus(error) === 409 && body.incomplete && !anyway) {
            setAsk({ who, anyway: true, message: `${body.detail} Sign anyway, as it is?` });
            return;
          }
          setAsk(null);
          toast.error(errorText(error, { fallback: 'Could not sign.' }));
        },
      },
    );
  }

  const officer = data.officer;
  const agent = data.agent;
  return (
    <div className="card bnf-q-sign">
      <h3>Signatures</h3>
      <div className="bnf-q-signrow">
        <div>
          <span className="bnf-q-label">{spec.officer_label}</span>
          <div className="bnf-q-signval">{officer ? `${officer.name} · signed` : 'Not yet signed'}</div>
        </div>
        <div>
          <span className="bnf-q-label">Licensed agent</span>
          <div className="bnf-q-signval">{agent ? `${agent.name} · signed` : 'Not yet signed'}</div>
        </div>
      </div>
      {(!agent || !officer) && (
        <div className="bnf-q-signform">
          <input
            className="bnf-intake-input"
            placeholder="Type the signer’s full name"
            aria-label="Signer’s full name"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
          {!agent && (
            <button type="button" className="btn btn-secondary btn-sm" disabled={!typed} onClick={() => setAsk({ who: 'agent', message: confirmWords('agent') })}>
              Sign as agent
            </button>
          )}
          {!officer && (
            <button
              type="button"
              className="btn btn-primary btn-sm"
              disabled={!typed || !authorized || data.lost}
              title={authorized ? 'Signing as the officer locks the questionnaire' : 'Tick that you hold the officer’s written authorization first'}
              onClick={() => setAsk({ who: 'officer', message: confirmWords('officer') })}
            >
              Sign for the company officer
            </button>
          )}
        </div>
      )}
      {!officer && (
        <label className="bnf-q-signauth">
          <input type="checkbox" checked={authorized} onChange={(event) => setAuthorized(event.target.checked)} />
          <span>
            I have the officer’s written authorization to sign for them. The client signs on their own link otherwise.
          </span>
        </label>
      )}
      <p className="bnf-q-note">
        Typed-name signature with a server timestamp. The officer’s signature locks the form and marks the Marketing
        Checklist item complete.
      </p>
      <ConfirmDialog
        open={Boolean(ask)}
        title={ask?.who === 'officer' ? 'Sign for the company officer' : 'Sign as the agent'}
        message={ask?.message}
        confirmLabel={ask?.anyway ? 'Sign anyway' : 'Sign'}
        busy={sign.isPending}
        onConfirm={() => run(ask.who, Boolean(ask.anyway))}
        onCancel={() => setAsk(null)}
      />
    </div>
  );
}
