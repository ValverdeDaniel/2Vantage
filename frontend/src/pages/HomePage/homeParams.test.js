import { describe, expect, it } from 'vitest';
import { changeHome, listQuery, pageWords, readHome, statusChips, viewParams, VIEWS } from './homeParams';

const url = (text) => new URLSearchParams(text);
const KEYS = { prospect: 'prospect', statuses: ['new_client', 'existing_client'] };

describe('the home views (CL10, OQ95)', () => {
  it('OQ95 lands on Prospects at the bare address', () => {
    expect(readHome(url('')).view).toBe('prospects');
    expect(readHome(url('view=queue')).view).toBe('prospects');
    expect(readHome(url('view=book')).view).toBe('book');
  });

  it('CL10 offers Prospects then Clients, the Work queue waiting for slice 61', () => {
    expect(VIEWS.map((view) => view.label)).toEqual(['Prospects', 'Clients']);
  });

  it('CL10 switching the view keeps only the view, as the old pill did', () => {
    expect(viewParams('book').toString()).toBe('view=book');
    expect(viewParams('prospects').toString()).toBe('');
  });
});

describe('the URL keeps the search and filters (§8.3)', () => {
  it('CL12 reads the search, chip, sort and page back', () => {
    expect(readHome(url('view=book&q=golden&status=existing_client&ordering=name&page=3'))).toEqual({
      view: 'book',
      q: 'golden',
      status: 'existing_client',
      ordering: 'name',
      page: 3,
    });
  });

  it('CL11 ignores a Clients chip on Prospects and a junk sort or page', () => {
    expect(readHome(url('status=new_client&ordering=-x&page=zero'))).toEqual({
      view: 'prospects',
      q: '',
      status: '',
      ordering: '',
      page: 1,
    });
  });

  it('CL12 a new search or chip goes back to page 1; defaults leave the URL', () => {
    const start = url('view=book&q=a&page=4');
    expect(changeHome(start, { q: 'ab' }).toString()).toBe('view=book&q=ab');
    expect(changeHome(start, { status: 'new_client' }).toString()).toBe('view=book&q=a&status=new_client');
    expect(changeHome(start, { q: '' }).toString()).toBe('view=book');
    expect(changeHome(start, { page: 5 }).toString()).toBe('view=book&q=a&page=5');
    expect(changeHome(start, { page: 1 }).toString()).toBe('view=book&q=a');
  });
});

describe('what each view asks the server for (CL11, CL12)', () => {
  it('CL11 Prospects lists Prospect clients only', () => {
    expect(listQuery(readHome(url('q=%20gold%20&page=2')), KEYS)).toEqual({
      q: 'gold',
      relationship: 'prospect',
      ordering: '',
      page: 2,
    });
  });

  it('CL12 Clients lists New and Existing clients, or the one its chip names', () => {
    expect(listQuery(readHome(url('view=book')), KEYS).relationship).toBe('new_client,existing_client');
    expect(listQuery(readHome(url('view=book&status=existing_client')), KEYS).relationship).toBe('existing_client');
    expect(listQuery(readHome(url('view=book&status=prospect')), KEYS).relationship).toBe(
      'new_client,existing_client',
    );
  });
});

describe('the Clients chips (CL12)', () => {
  it('CL12 offers All · New clients · Existing clients, from the served statuses', () => {
    const statuses = [
      { key: 'new_client', label: 'New client' },
      { key: 'existing_client', label: 'Existing client' },
    ];
    expect(statusChips(statuses).map((chip) => chip.label)).toEqual(['All', 'New clients', 'Existing clients']);
    expect(statusChips(statuses).map((chip) => chip.key)).toEqual(['', 'new_client', 'existing_client']);
  });
});

describe('the pager (§8.3: 25 rows a page)', () => {
  it('CL12 hides when everything fits, and never runs past the last page', () => {
    expect(pageWords(1, 25)).toBeNull();
    expect(pageWords(1, 26)).toEqual({ page: 1, pages: 2 });
    expect(pageWords(9, 51)).toEqual({ page: 3, pages: 3 });
  });
});
