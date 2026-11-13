import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { placeCards } from './placeCards';

const SAME = (a, b) =>
  a.height === b.height &&
  Object.keys(a.tops).length === Object.keys(b.tops).length &&
  Object.keys(a.tops).every((ref) => a.tops[ref] === b.tops[ref]);

/*
 * The comment margin (plan.md §8.8; L31; old 891f1b3 `reviewrequest/CommentMargin.jsx`, D-162): the column beside a form
 * where each item's conversation lives, Google Docs style, never inside the item. `rootRef` the form the cards sit
 * beside (form and margin share one scroll); `refs` the cards in the form's order; `anchorOf(ref)` the item's element
 * (none: the card follows the one before); `activeRef` the picked card, lined up with its item, which gets
 * `cm-anchor-on`; `children(ref)` the card. It measures before paint whenever the form, a card or the window changes,
 * and a new card stays hidden until measured, so it never slides in from the top.
 */
export default function CommentMargin({ rootRef, refs, anchorOf, activeRef = '', gap = 10, children }) {
  const boxRef = useRef(null);
  const cards = useRef(new Map());
  const frame = useRef(0);
  const [layout, setLayout] = useState({ tops: {}, height: 0 });
  const anchorRef = useRef(anchorOf);
  const live = useRef({ refs, activeRef, gap });
  useLayoutEffect(() => {
    anchorRef.current = anchorOf;
    live.current = { refs, activeRef, gap };
  });
  const refsKey = refs.join('\n');

  const measure = useCallback(() => {
    frame.current = 0;
    const box = boxRef.current;
    if (!box) return;
    const { refs: list, activeRef: picked, gap: room } = live.current;
    const base = box.getBoundingClientRect().top;
    let last = 0;
    const rows = [];
    list.forEach((ref, i) => {
      const el = cards.current.get(ref);
      if (!el) return;
      const anchor = anchorRef.current(ref);
      const want = anchor ? Math.round(anchor.getBoundingClientRect().top - base) : last;
      last = want;
      rows.push({ ref, want, height: el.offsetHeight, i });
    });
    rows.sort((a, b) => a.want - b.want || a.i - b.i);
    const tops = placeCards(rows.map((r) => r.want), rows.map((r) => r.height), rows.findIndex((r) => r.ref === picked), room);
    const next = { tops: {}, height: 0 };
    rows.forEach((r, i) => {
      next.tops[r.ref] = Math.round(tops[i]);
      next.height = Math.max(next.height, Math.round(tops[i] + r.height));
    });
    setLayout((prev) => (SAME(prev, next) ? prev : next));
  }, []);

  const schedule = useCallback(() => {
    if (!frame.current) frame.current = requestAnimationFrame(measure);
  }, [measure]);

  useLayoutEffect(() => {
    measure();
  });

  useEffect(() => {
    const root = rootRef?.current || null;
    const sizes = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(schedule) : null;
    if (sizes) {
      if (root) sizes.observe(root);
      cards.current.forEach((el) => sizes.observe(el));
    }
    const dom = root && typeof MutationObserver !== 'undefined' ? new MutationObserver(schedule) : null;
    dom?.observe(root, { childList: true, subtree: true });
    window.addEventListener('resize', schedule);
    return () => {
      sizes?.disconnect();
      dom?.disconnect();
      window.removeEventListener('resize', schedule);
      if (frame.current) cancelAnimationFrame(frame.current);
      frame.current = 0;
    };
  }, [rootRef, schedule, refsKey]);

  useEffect(() => {
    if (!activeRef) return undefined;
    const el = anchorRef.current(activeRef);
    if (!el) return undefined;
    el.classList.add('cm-anchor-on');
    return () => el.classList.remove('cm-anchor-on');
  }, [activeRef, refsKey]);

  return (
    <div ref={boxRef} className="cm-margin" style={layout.height ? { minHeight: layout.height } : undefined}>
      {refs.map((ref) => {
        const top = layout.tops[ref];
        return (
          <div
            key={ref}
            ref={(el) => {
              if (el) cards.current.set(ref, el);
              else cards.current.delete(ref);
            }}
            className={`cm-slot${ref === activeRef ? ' cm-slot-on' : ''}`}
            data-margin-ref={ref}
            style={top === undefined ? { visibility: 'hidden' } : { top }}
          >
            {children(ref)}
          </div>
        );
      })}
    </div>
  );
}
