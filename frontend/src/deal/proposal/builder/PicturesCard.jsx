import { useState } from 'react';
import { pictureThumbUrl, useCoverImages, useUploadCover } from '../../../api/proposalFirm';
import { errorText } from '../../../lib/errors';
import { useToast } from '../../../ui/useToast';
import BuilderCard from '../../shared/BuilderCard';

/*
 * Which picture each of the Presentation format's dark pages wears (plan.md §8.14; J35; the old PicturesCard.jsx at
 * 891f1b3, same words and classes), in the PDF and the PowerPoint alike. Every place takes None, a stock picture or
 * one of the firm's uploads, and has its own Upload (the 2026-11-05 call). A place stores its pick at
 * `output.pictures.<place>` ("upload:<id>" for an upload); the cover's upload is the Cover card's
 * `output.cover.image`, because the spreadsheet's banner reads that alone. A place the deal never touched reads the
 * server's default. An optional card: its mark never counts toward "n of N completed". The places and the stock
 * pictures are `/api/meta/` proposal.pictures; the tiles are the server's thumbnails.
 */
export default function PicturesCard({ output, meta, card, busy, onSet, onSetMany }) {
  const toast = useToast();
  const covers = useCoverImages();
  const upload = useUploadCover();
  const [uploading, setUploading] = useState('');
  const catalog = meta.pictures;
  const uploads = (covers.data ?? []).map((image, n) => ({ key: image.key, id: image.id, label: image.label || `Your image ${n + 1}` }));
  const tiles = [...catalog.stock, ...uploads];
  const coverUpload = uploads.find((image) => image.id === output.cover.image);
  const picked = (place) => (place === 'cover' && coverUpload ? coverUpload.key : output.pictures[place]);
  const labelOf = (key) => tiles.find((image) => image.key === key)?.label;
  const chosen = catalog.places.filter((place) => labelOf(picked(place.key))).map((place) => `${place.label}: ${labelOf(picked(place.key))}`);

  const pick = (place, key) => {
    if (place !== 'cover') return onSet(`output.pictures.${place}`, key);
    const found = uploads.find((image) => image.key === key);
    if (found) return onSet('output.cover.image', found.id);
    return onSetMany({ 'output.cover.image': null, 'output.pictures.cover': key });
  };
  const add = async (place, file) => {
    if (!file) return;
    setUploading(place);
    try {
      const made = await upload.mutateAsync({ file });
      await (place === 'cover' ? onSet('output.cover.image', made.id) : onSet(`output.pictures.${place}`, made.key));
      toast.success('Picture added and picked for this page');
    } catch (error) {
      toast.error(errorText(error, { fallback: 'Could not upload the picture' }));
    } finally {
      setUploading('');
    }
  };
  const coverNote = () => {
    if (!output.cover.on) return 'No cover page on this proposal';
    return coverUpload ? 'Your upload is the cover image' : '';
  };

  return (
    <BuilderCard guide="build-pictures" title="Pictures" summary={chosen.length ? chosen.join(' · ') : 'No pictures'} card={card}>
      <div className="bb-panel-sub">
        A picture on the dark pages of the PDF and the PowerPoint: one of ours, or upload your own. The client
        spreadsheet never shows these, except an upload on the cover.
      </div>
      {covers.isError && <div className="bnf-output-hint">Could not load the firm&apos;s uploads.</div>}
      {catalog.places.map((place) => {
        const note = place.key === 'cover' ? coverNote() : '';
        const on = picked(place.key);
        return (
          <div key={place.key} className="bnf-pic-row">
            <div className="bnf-pic-place">
              {place.label}
              {note && <span className="bnf-pic-note">{note}</span>}
            </div>
            <div className="bnf-pic-tiles" role="group" aria-label={`Picture on ${place.label}`}>
              <button
                type="button"
                className={`bnf-pic-tile bnf-pic-none${on ? '' : ' bnf-pic-tile-on'}`}
                aria-pressed={!on}
                disabled={busy}
                onClick={() => pick(place.key, null)}
              >
                None
              </button>
              {tiles.map((image) => (
                <button
                  key={image.key}
                  type="button"
                  className={`bnf-pic-tile${on === image.key ? ' bnf-pic-tile-on' : ''}`}
                  aria-pressed={on === image.key}
                  aria-label={image.label}
                  title={image.label}
                  disabled={busy}
                  onClick={() => pick(place.key, image.key)}
                >
                  <img src={pictureThumbUrl(image.key)} alt="" loading="lazy" />
                </button>
              ))}
              <label
                className={`bnf-pic-tile bnf-pic-upload${busy || uploading ? ' is-disabled' : ''}`}
                title={`Upload a PNG or JPEG for ${place.label}`}
              >
                {uploading === place.key ? 'Uploading…' : '＋ Upload'}
                <input
                  type="file"
                  accept="image/png,image/jpeg"
                  disabled={busy || Boolean(uploading)}
                  aria-label={`Upload a picture for ${place.label}`}
                  onChange={(event) => {
                    add(place.key, event.target.files?.[0]);
                    event.target.value = '';
                  }}
                />
              </label>
            </div>
          </div>
        );
      })}
    </BuilderCard>
  );
}
