import { useState } from 'react';
import { Link } from 'react-router';
import { labelOf, relationshipLabel, relationships } from '../../../api/meta';
import { errorText } from '../../../lib/errors';
import FactRow from '../../../ui/FactRow';
import { clientPath } from '../clientTabs';
import SelectRow from './SelectRow';

// The Status select: every status in meta order, the current one first-class and each move the status door offers
// greyed with its sentence when refused (§5.1; the server decides, never the browser).
function statusOptions(client, meta) {
  const moves = Object.fromEntries((client.moves || []).map((move) => [move.to, move]));
  return relationships(meta)
    .filter((status) => status.key === client.relationship || moves[status.key])
    .map((status) => {
      const move = moves[status.key];
      return {
        value: status.key,
        label: relationshipLabel(meta, status.key),
        disabled: Boolean(move && !move.allowed),
        title: move && !move.allowed ? move.sentence : undefined,
      };
    });
}

function contactOptions(client) {
  return (client.contacts || []).map((contact) => ({
    value: String(contact.id),
    label: `${contact.name || '—'}${contact.role_label ? ` · ${contact.role_label}` : ''}`,
  }));
}

/**
 * The header card's facts (plan.md §8.5; CL16, H41; old ClientHeaderCard.jsx's snapshot grid at 891f1b3): Client name
 * (deals' PATCH), Status (a select on the status door, rule 6), Primary producer (read-only, "set ▸" to the client's
 * split on its Commissions tab, slice 68), Main contact (a select that sets the
 * primary) and its details, Employees (the one headcount, with where it came from), Funding (the incumbent's), then
 * Legal name, FEIN, SIC code and Situs state read-only from the deal's intake, with "edit in intake ↗". The old Service
 * owner, Lines of business and External ref are dropped (CL28).
 */
export default function ClientFacts({ client, overview, meta, writes }) {
  const [errors, setErrors] = useState({});
  const facts = overview.facts;
  const settle = (row) => ({
    onSuccess: () => setErrors((current) => ({ ...current, [row]: '' })),
    onError: (error) => setErrors((current) => ({ ...current, [row]: errorText(error) })),
  });
  const contacts = contactOptions(client);
  const primary = (client.contacts || []).find((contact) => contact.id === client.primary_id);
  const year = overview.history.find((row) => row.deal_id === facts?.deal_id)?.year;
  const employees = facts?.employees;
  return (
    <div className="bnf-ov-facts">
      <div className="bnf-snapshot-grid">
        <FactRow
          label="Client name"
          value={client.name}
          placeholder="Employer name"
          error={errors.name}
          onCommit={(raw) => raw && writes.update.mutate({ name: raw }, settle('name'))}
        />
        <SelectRow
          label="Status"
          value={client.relationship}
          options={statusOptions(client, meta)}
          disabled={writes.setStatus.isPending}
          error={errors.status}
          onChange={(to) => to !== client.relationship && writes.setStatus.mutate(to, settle('status'))}
        />
        <FactRow
          label="Primary producer"
          hint="synced from who-gets-what — change it on the Commissions tab"
          value={client.owner?.name || ''}
          readOnly
          after={
            !client.owner ? (
              <Link className="bnf-override-link" to={clientPath(client.id, 'commissions')}>
                {' '}
                set ▸
              </Link>
            ) : null
          }
        />
        <SelectRow
          label="Main contact"
          hint="the client's, across its deals — from its contacts"
          value={client.primary_id ? String(client.primary_id) : ''}
          options={contacts}
          empty={contacts.length ? '— pick a contact —' : '— add contacts on a deal —'}
          disabled={!contacts.length || writes.setPrimary.isPending}
          error={errors.contact}
          onChange={(id) => id && writes.setPrimary.mutate(Number(id), settle('contact'))}
        />
        {primary && (primary.email || primary.phone) && (
          <FactRow label="Contact details" value={[primary.email, primary.phone].filter(Boolean).join(' · ')} readOnly />
        )}
        {facts && (
          <>
            <FactRow
              label="Employees"
              hint={employees.from_label ? `from ${employees.from_label}` : ''}
              value={employees.value == null ? '' : `${employees.value}${employees.estimate ? ' (estimate)' : ''}`}
              readOnly
            />
            <FactRow label="Funding" value={labelOf(meta?.funding, facts.funding.value)} readOnly />
            <FactRow label="Legal name" hint={year ? `from the ${year} deal` : ''} value={facts.legal_name} readOnly />
            <FactRow label="FEIN" value={facts.fein} readOnly />
            <FactRow label="SIC code" value={facts.sic_code} readOnly />
            <FactRow
              label="Situs state"
              value={facts.situs_state}
              readOnly
              after={
                <Link className="bnf-override-link" to={`/deals/${facts.deal_id}/intake`}>
                  {' '}
                  edit in intake ↗
                </Link>
              }
            />
          </>
        )}
      </div>
    </div>
  );
}
