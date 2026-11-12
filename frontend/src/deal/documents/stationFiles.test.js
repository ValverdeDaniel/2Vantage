import { describe, expect, it } from 'vitest';
import { chooseFile, firstDataFile, inUploadOrder, proposalFiles } from './stationFiles';

const file = (id, bucket, uploaded_at) => ({ id, bucket, uploaded_at });
const invoice = file(1, 'intake', '2026-11-01T10:00:00Z');
const census = file(2, 'census', '2026-11-02T10:00:00Z');
const quote = file(3, 'proposal', '2026-11-03T10:00:00Z');
const renewal = file(4, 'proposal', '2026-11-04T10:00:00Z');
const newestFirst = [renewal, quote, census, invoice];

describe('E1 the station files', () => {
  it('runs the tabs in upload order, oldest first', () => {
    expect(inUploadOrder(newestFirst).map((f) => f.id)).toEqual([1, 2, 3, 4]);
  });

  it('opens a file whose data is on screen when nothing is asked', () => {
    const files = inUploadOrder(newestFirst);
    expect(firstDataFile(files).id).toBe(3);
    expect(firstDataFile([invoice, census]).id).toBe(2);
    expect(firstDataFile([])).toBe(null);
    expect(proposalFiles(files).map((f) => f.id)).toEqual([3, 4]);
  });

  it('E3 shows the first proposal file for All proposals', () => {
    expect(chooseFile({ asked: 'proposals', files: inUploadOrder(newestFirst) })).toEqual({
      file: quote,
      all: true,
      missing: false,
    });
  });

  it('E18 opens the asked file, a value file, or a removed file, and says when the file is gone', () => {
    const files = inUploadOrder(newestFirst);
    const removed = [file(9, 'proposal', '2026-10-01T10:00:00Z')];
    expect(chooseFile({ asked: '2', files }).file.id).toBe(2);
    expect(chooseFile({ asked: '', files, sourceDoc: 4 }).file.id).toBe(4);
    expect(chooseFile({ asked: '9', files, removed }).file.id).toBe(9);
    expect(chooseFile({ asked: '77', files, removed })).toEqual({ file: quote, all: false, missing: true });
  });
});
