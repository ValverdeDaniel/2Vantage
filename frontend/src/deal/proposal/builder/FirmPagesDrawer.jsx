import { useState } from 'react';
import { useFirmPages, useSaveFirmPages, useTeam, useTeamWrites } from '../../../api/proposalFirm';
import { errorText } from '../../../lib/errors';
import Drawer from '../../../ui/Drawer';
import Loading from '../../../ui/Loading';
import { useToast } from '../../../ui/useToast';
import FirmPerson from './FirmPerson';
import FirmStory from './FirmStory';

/*
 * The Firm pages drawer (plan.md §8.14; J155, OQ41; the old FirmPagesPanel.jsx at 891f1b3, "The firm on a
 * presentation", same words and classes): who the firm is, its figures, its meeting calendar and its people, stored
 * once and read by every proposal, open to every user. The logo, the brand colour and the contact stay in Django
 * admin (rule 6). It opens from the Presentation pages card and from a firm page's Fix ▸ on the ledger; each edit
 * refetches the builder, whose ledger then says the page prints.
 */
export default function FirmPagesDrawer({ open, meta, onClose }) {
  const toast = useToast();
  const pages = useFirmPages(open);
  const team = useTeam(open);
  const savePages = useSaveFirmPages();
  const writes = useTeamWrites();
  const [newName, setNewName] = useState('');
  const limits = meta.firm;
  const run = (promise) =>
    promise.catch((error) => {
      toast.error(errorText(error, { fallback: 'Could not save that' }));
      return null;
    });
  const addPerson = async () => {
    const name = newName.trim();
    if (!name) return;
    if (await run(writes.add.mutateAsync({ name }))) setNewName('');
  };
  const people = team.data ?? [];

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title="Firm pages"
      sub="The firm on a presentation: stored once and read by every proposal. A section left empty prints no page."
    >
      {pages.isPending || team.isPending ? (
        <Loading label="Loading the firm pages…" />
      ) : (
        <div className="bnf-docs-panel" data-guide="firm-pages">
          {pages.data && (
            <FirmStory
              key={pages.dataUpdatedAt ? 'loaded' : 'empty'}
              pages={pages.data}
              limits={limits}
              onSave={(change) => run(savePages.mutateAsync(change))}
            />
          )}
          <div className="bnf-present-block">
            <div className="bnf-present-head">Your team</div>
            {people.map((member) => (
              <FirmPerson key={member.id} member={member} limits={limits} writes={writes} run={run} />
            ))}
            {people.length < limits.team && (
              <div className="bnf-present-year">
                <input
                  type="text"
                  maxLength={120}
                  placeholder="Name"
                  aria-label="New team member's name"
                  value={newName}
                  onChange={(event) => setNewName(event.target.value)}
                  onKeyDown={(event) => event.key === 'Enter' && addPerson()}
                />
                <button type="button" className="btn btn-secondary btn-sm" disabled={!newName.trim() || writes.add.isPending} onClick={addPerson}>
                  ＋ Add a person
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </Drawer>
  );
}
