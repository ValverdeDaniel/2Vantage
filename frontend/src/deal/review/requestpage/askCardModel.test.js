import { describe, expect, it } from 'vitest';
import {
  bodyOf,
  changeCount,
  emptyChange,
  itemState,
  partValue,
  targetOf,
  tickAction,
  updateWords,
  withColumn,
  withOff,
  withPart,
  withSetting,
} from './askCardModel';

const target = {
  request_id: 7,
  link_ids: [11, 12],
  parts: { intake: 'selected', blocks: [], census: 'none', census_columns: [], census_file: false, documents_missing: true },
  on_link: ['intake:fein', 'intake:dba'],
  drafted: { 'intake:website': 41 },
};
const item = (ref, status = 'missing') => ({ ref, status });

describe('the Ask card (L42)', () => {
  it('L42 reads the target from the address', () => {
    const params = (raw) => new URLSearchParams(raw);
    expect(targetOf(params('target=link:12'))).toEqual({ kind: 'link', id: 12 });
    expect(targetOf(params('target=new'))).toEqual({ kind: 'new' });
    expect(targetOf(params('target=link:x'))).toBeNull();
    expect(targetOf(params(''))).toBeNull();
  });

  it('L42 says where an item stands on the picked link and what a tick does', () => {
    const change = withOff(emptyChange(), 'intake:dba');
    expect(itemState(item('intake:fein', 'asked'), target, change)).toBe('on_link');
    expect(itemState(item('intake:dba', 'asked'), target, change)).toBe('coming_off');
    expect(itemState(item('intake:website', 'in_cart'), target, change)).toBe('will_add');
    expect(itemState(item('intake:sic_code'), target, change)).toBe('missing');
    expect(tickAction(item('intake:fein'), target, change)).toEqual({ kind: 'off', ref: 'intake:fein' });
    expect(tickAction(item('intake:dba'), target, change)).toEqual({ kind: 'keep', ref: 'intake:dba' });
    expect(tickAction(item('intake:website'), target, change)).toEqual({ kind: 'undraft', id: 41 });
    expect(tickAction(item('intake:sic_code'), target, change)).toEqual({ kind: 'draft', ref: 'intake:sic_code' });
  });

  it('L42 part switches: on, a scope change, off, and back to how it was', () => {
    let change = withPart(emptyChange(), target, 'census', 'missing');
    expect(change.on.census).toBe('missing');
    expect(partValue(target, change, 'census')).toBe('missing');
    change = withPart(change, target, 'intake', '');
    expect(change.off.parts).toEqual(['intake']);
    expect(partValue(target, change, 'intake')).toBe('');
    change = withPart(change, target, 'intake', 'selected');
    expect(change.off.parts).toEqual([]);
    change = withPart(change, target, 'documents_missing', false);
    expect(change.on.documents_missing).toBe(false);
    change = withPart(change, target, 'documents_missing', true);
    expect(change.on.documents_missing).toBeNull();
  });

  it('L36 L39 the body carries the drafts, what comes off and on, the level and each person’s settings', () => {
    let change = withOff(emptyChange(), 'intake:dba');
    change = withColumn(change, 'dob', false);
    change = withSetting(change, 11, 'blank', true);
    change = { ...change, security: 'pin' };
    expect(bodyOf(change, target)).toEqual({
      ids: [41],
      off: { refs: ['intake:dba'] },
      on: { columns: ['dob'] },
      security: 'pin',
      settings: { 11: { blank: true } },
    });
    expect(changeCount(change, target)).toBe(5);
    expect(withSetting(change, 11, 'blank', null).settings).toEqual({});
    expect(bodyOf(emptyChange(), {})).toEqual({ ids: [] });
  });

  it('L42 words the button by the links it reaches', () => {
    expect(updateWords(target, false)).toBe('Update 2 links');
    expect(updateWords({ link_ids: [3] }, false)).toBe('Update link');
    expect(updateWords(target, true)).toBe('Updating…');
  });
});
