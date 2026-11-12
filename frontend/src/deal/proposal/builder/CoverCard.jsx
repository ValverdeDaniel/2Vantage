import { useState } from 'react';
import { useCoverImages, useCoverTiles, useDeleteCover, useUploadCover } from '../../../api/proposalFirm';
import { errorText } from '../../../lib/errors';
import { useToast } from '../../../ui/useToast';
import BuilderCard from '../../shared/BuilderCard';
import CoverWords from './CoverWords';
import useCoverThumbs from './useCoverThumbs';

/*
 * The proposal's cover (plan.md §8.14; J32–J34; the old CoverPicker.jsx at 891f1b3, same words and classes): the
 * Cover page switch, the tiles — the Presentation format's own cover ("Vantage", wearing the cover's stock picture),
 * then each of the firm's uploads — drawn by pdf.js from one server PDF (`proposal/covers/`, built from thumbnails
 * behind an ETag; a Retry per tile, J.5 B19), ＋ Upload a cover (picked at once), × to delete an upload for everyone,
 * and the title and introduction. Picking writes `output.cover.image` (an upload's id, or null for the Vantage
 * design); a deleted upload reads as the Vantage design, as the files fall back. The six white Classic designs wait
 * with Classic (J143).
 */
export default function CoverCard({ output, words, client, meta, card, busy, onSet }) {
  const toast = useToast();
  const covers = useCoverImages();
  const upload = useUploadCover();
  const remove = useDeleteCover();
  const [version, setVersion] = useState(0);
  const coverOn = output.cover.on;
  const list = covers.data ?? [];
  const picked = list.some((image) => image.id === output.cover.image) ? output.cover.image : null;
  const tiles = useCoverTiles(output.pictures.cover, `${version}:${list.map((image) => image.id).join(',')}`, covers.isSuccess);
  const drawn = useCoverThumbs(tiles.data);
  const all = [{ key: 'vantage', label: 'Vantage', id: null }, ...list.map((image, n) => ({ ...image, label: image.label || `Your image ${n + 1}` }))];
  const pickedLabel = all.find((tile) => tile.id === picked)?.label ?? 'Vantage';
  const failed = tiles.isError || drawn.failed.has('all');

  const add = async (file) => {
    if (!file) return;
    try {
      const made = await upload.mutateAsync({ file });
      await onSet('output.cover.image', made.id);
      toast.success('Cover image added and picked for this proposal');
    } catch (error) {
      toast.error(errorText(error, { fallback: 'Could not upload the cover image' }));
    }
  };
  const del = async (tile) => {
    const ok = window.confirm(
      `Delete "${tile.label}" for everyone? Proposals that use it go back to their built-in design, and pages that ` +
        'wear it go without a picture.',
    );
    if (!ok) return;
    try {
      await remove.mutateAsync(tile.id);
      if (picked === tile.id) await onSet('output.cover.image', null);
      toast.success('Cover image deleted');
    } catch (error) {
      toast.error(errorText(error, { fallback: 'Could not delete the cover image' }));
    }
  };
  const retry = (index) => (tiles.isError ? setVersion((n) => n + 1) : drawn.retry(drawn.failed.has('all') ? 'all' : index));

  return (
    <BuilderCard
      guide="build-cover"
      className="bnf-cover-strip"
      title="Cover"
      summary={coverOn ? `${pickedLabel}${picked ? ' · also tops the spreadsheet' : ''}` : 'No cover page'}
      card={card}
    >
      <div className="bnf-cover-head">
        <label className="bnf-output-check">
          <input type="checkbox" checked={coverOn} disabled={busy} onChange={(event) => onSet('output.cover.on', event.target.checked)} />
          Cover page
        </label>
      </div>
      {failed && (
        <div className="bnf-output-hint">
          {tiles.isError ? 'Could not load the cover previews.' : 'This browser could not draw the cover previews.'}{' '}
          Picking a cover still works, and the PDF still prints it.{' '}
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => retry('all')}>
            Try again
          </button>
        </div>
      )}
      <div className={`bnf-cover-tiles${coverOn ? '' : ' bnf-cover-tiles-off'}`}>
        {all.map((tile, index) => {
          const on = tile.id === picked;
          const lost = drawn.failed.has(index);
          return (
            <div key={tile.key} className={`bnf-cover-tile${on ? ' bnf-cover-tile-on' : ''}`}>
              <button
                type="button"
                className="bnf-cover-pick"
                aria-pressed={on}
                disabled={!coverOn || busy}
                title={tile.label}
                onClick={() => onSet('output.cover.image', tile.id)}
              >
                {drawn.thumbs[index] ? (
                  <img src={drawn.thumbs[index]} alt="" />
                ) : (
                  <span className="bnf-cover-wait">{lost || failed ? 'Couldn’t draw' : tiles.data ? 'Drawing…' : 'Loading…'}</span>
                )}
                <span className="bnf-cover-label">{tile.label}</span>
              </button>
              {lost && !failed && (
                <button type="button" className="bnf-override-link" onClick={() => retry(index)}>
                  Retry
                </button>
              )}
              {tile.id && (
                <button
                  type="button"
                  className="bnf-cover-del"
                  aria-label={`Delete ${tile.label}`}
                  title="Delete this cover image"
                  disabled={remove.isPending}
                  onClick={() => del(tile)}
                >
                  ×
                </button>
              )}
            </div>
          );
        })}
        {list.length < meta.firm.cover_images && (
          <label className="bnf-cover-tile bnf-cover-upload" aria-busy={upload.isPending || undefined}>
            <input
              type="file"
              accept=".png,.jpg,.jpeg"
              hidden
              disabled={upload.isPending}
              onChange={(event) => {
                add(event.target.files?.[0]);
                event.target.value = '';
              }}
            />
            <span className="bnf-cover-upload-plus">＋</span>
            <span className="bnf-cover-label">{upload.isPending ? 'Uploading…' : 'Upload a cover'}</span>
          </label>
        )}
      </div>
      <CoverWords words={words} client={client} meta={meta} busy={busy} onSet={onSet} />
    </BuilderCard>
  );
}
