import { describe, expect, it } from 'vitest';
import { changed, cursorAction, editorAction, rowEdge, step } from './gridKeys';

const R = ['41', '42', '43'];
const C = ['rate_ee', 'rate_es', 'rate_fam'];

describe('F69 step', () => {
  it('moves by rows and columns and stops at the edges', () => {
    expect(step(R, C, { r: '41', c: 'rate_ee' }, 1, 0)).toEqual({ r: '42', c: 'rate_ee' });
    expect(step(R, C, { r: '41', c: 'rate_ee' }, -1, 0)).toEqual({ r: '41', c: 'rate_ee' });
    expect(step(R, C, { r: '43', c: 'rate_fam' }, 0, 1)).toEqual({ r: '43', c: 'rate_fam' });
  });

  it('wraps Tab to the next row and Shift+Tab to the previous one', () => {
    expect(step(R, C, { r: '41', c: 'rate_fam' }, 0, 1, true)).toEqual({ r: '42', c: 'rate_ee' });
    expect(step(R, C, { r: '42', c: 'rate_ee' }, 0, -1, true)).toEqual({ r: '41', c: 'rate_fam' });
    expect(step(R, C, { r: '43', c: 'rate_fam' }, 0, 1, true)).toEqual({ r: '43', c: 'rate_fam' });
    expect(step(R, C, { r: '41', c: 'rate_ee' }, 0, -1, true)).toEqual({ r: '41', c: 'rate_ee' });
  });

  it('leaves a cell that is no longer on the grid where it is', () => {
    const gone = { r: '99', c: 'rate_ee' };
    expect(step(R, C, gone, 1, 0)).toBe(gone);
  });

  it('reads numbers and strings as the same keys', () => {
    expect(step(R, C, { r: 41, c: 'rate_ee' }, 1, 0)).toEqual({ r: '42', c: 'rate_ee' });
  });

  it('Home and End go to the row edges', () => {
    expect(rowEdge(C, { r: '42', c: 'rate_es' }, false)).toEqual({ r: '42', c: 'rate_ee' });
    expect(rowEdge(C, { r: '42', c: 'rate_es' }, true)).toEqual({ r: '42', c: 'rate_fam' });
  });
});

describe('F69 cursorAction', () => {
  it('moves with Enter, Tab and the arrows', () => {
    expect(cursorAction({ key: 'Enter' })).toEqual({ type: 'move', dr: 1, dc: 0, wrap: false });
    expect(cursorAction({ key: 'Enter', shiftKey: true })).toEqual({ type: 'move', dr: -1, dc: 0, wrap: false });
    expect(cursorAction({ key: 'Tab' })).toEqual({ type: 'move', dr: 0, dc: 1, wrap: true });
    expect(cursorAction({ key: 'Tab', shiftKey: true })).toEqual({ type: 'move', dr: 0, dc: -1, wrap: true });
    expect(cursorAction({ key: 'ArrowLeft' })).toEqual({ type: 'move', dr: 0, dc: -1, wrap: false });
    expect(cursorAction({ key: 'ArrowDown' })).toEqual({ type: 'move', dr: 1, dc: 0, wrap: false });
    expect(cursorAction({ key: 'Home' })).toEqual({ type: 'home' });
    expect(cursorAction({ key: 'End' })).toEqual({ type: 'end' });
  });

  it('F2 edits the value, typing replaces it, Delete and Backspace open an empty box', () => {
    expect(cursorAction({ key: 'F2' })).toEqual({ type: 'edit', seed: null, typed: false });
    expect(cursorAction({ key: '7' })).toEqual({ type: 'edit', seed: '7', typed: true });
    expect(cursorAction({ key: 'Delete' })).toEqual({ type: 'edit', seed: '', typed: true });
    expect(cursorAction({ key: 'Backspace' })).toEqual({ type: 'edit', seed: '', typed: true });
  });

  it('F70 Ctrl+Z and ⌘Z undo; Escape drops the cursor; other shortcuts pass through', () => {
    expect(cursorAction({ key: 'z', ctrlKey: true })).toEqual({ type: 'undo' });
    expect(cursorAction({ key: 'Z', metaKey: true })).toEqual({ type: 'undo' });
    expect(cursorAction({ key: 'z', ctrlKey: true, shiftKey: true })).toBeNull();
    expect(cursorAction({ key: 'Escape' })).toEqual({ type: 'deselect' });
    expect(cursorAction({ key: 'c', ctrlKey: true })).toBeNull();
    expect(cursorAction({ key: 'Shift' })).toBeNull();
  });
});

describe('F69 editorAction', () => {
  it('commits and moves on Enter and Tab, cancels on Escape', () => {
    expect(editorAction({ key: 'Enter' }, false)).toEqual({ type: 'commit', move: [1, 0, false] });
    expect(editorAction({ key: 'Enter', shiftKey: true }, false)).toEqual({ type: 'commit', move: [-1, 0, false] });
    expect(editorAction({ key: 'Tab', shiftKey: true }, true)).toEqual({ type: 'commit', move: [0, -1, true] });
    expect(editorAction({ key: 'Escape' }, true)).toEqual({ type: 'cancel' });
  });

  it('arrows commit an edit begun by typing, and move the caret in one opened by F2 or a click', () => {
    expect(editorAction({ key: 'ArrowRight' }, true)).toEqual({ type: 'commit', move: [0, 1, false] });
    expect(editorAction({ key: 'ArrowRight' }, false)).toEqual({ type: 'caret' });
    expect(editorAction({ key: 'a' }, true)).toBeNull();
  });

  it('an unchanged value writes nothing', () => {
    expect(changed('3300', ' 3300 ')).toBe(false);
    expect(changed('', null)).toBe(false);
    expect(changed('3300', '3500')).toBe(true);
    expect(changed('3300', '')).toBe(true);
  });
});
