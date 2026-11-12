import { useState } from 'react';

/*
 * How the Scanned data panel shows a file's values, remembered in this browser only (plan.md §8.16; E35, E65, D121;
 * the old DocumentsTab's `vantage.documents.view` and `vantage.documents.review`): the List (worst first, beside the
 * file), the Grid (side by side) or ▤ As in the file (a quote's printed table, beside the file; slice 21), and Review
 * mode, where the file follows the value you are on. ✎ Edit is not
 * remembered: it is a session, and Review and Edit are never on together (`editing` turns Review's keys off).
 */

const VIEW_KEY = 'vantage.documents.view';
const REVIEW_KEY = 'vantage.documents.review';

function read(key) {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null; // a private window
  }
}

function write(key, value) {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    /* a private window: the choice lasts until the page is left */
  }
}

export default function useStationModes() {
  const [view, setView] = useState(() => (['grid', 'file'].includes(read(VIEW_KEY)) ? read(VIEW_KEY) : 'list'));
  const [review, setReview] = useState(() => read(REVIEW_KEY) === '1');
  const [editing, setEditing] = useState(false);
  return {
    view,
    review: review && !editing,
    editing,
    pickView(next) {
      setView(next);
      write(VIEW_KEY, next);
    },
    setReview(next) {
      setReview(next);
      write(REVIEW_KEY, next ? '1' : '0');
    },
    /** ✎ Edit pressed (from Review too: it keeps the keyboard), or Done ✓. */
    setEditing(next) {
      setEditing(next);
      if (next && review) {
        setReview(false);
        write(REVIEW_KEY, '0');
      }
    },
  };
}
