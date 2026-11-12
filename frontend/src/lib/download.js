// Downloads from the API keep the server's file name (Content-Disposition, plan.md §3.6).
import api from '../api/client';

/** File name from a Content-Disposition header (RFC 5987 filename* first), or ''. */
export function filenameFrom(disposition) {
  if (!disposition) return '';
  const star = /filename\*\s*=\s*([^']*)'[^']*'([^;]+)/i.exec(disposition);
  if (star) {
    try {
      return decodeURIComponent(star[2].trim().replace(/^"|"$/g, ''));
    } catch {
      /* fall through to the plain form */
    }
  }
  const plain = /filename\s*=\s*"([^"]*)"|filename\s*=\s*([^;]+)/i.exec(disposition);
  return plain ? (plain[1] ?? plain[2]).trim() : '';
}

function apiPath(url) {
  return url.startsWith('/api/') ? url.slice('/api/'.length) : url;
}

function saveBlob(blob, filename) {
  const href = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = href;
  link.download = filename;
  link.style.display = 'none';
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(href), 1000);
}

// A failed blob request carries its JSON error body as a Blob: parse it so errorText() can read it.
async function parseBlobError(error) {
  const data = error?.response?.data;
  if (data instanceof Blob && /json/i.test(data.type)) {
    try {
      error.response.data = JSON.parse(await data.text());
    } catch {
      /* keep the original body */
    }
  }
  return error;
}

/**
 * Fetches a file through the API client (session, CSRF retry, readable errors) and saves it under the server's
 * file name. `url` is relative to /api ('documents/4/download/') or absolute ('/api/documents/4/download/').
 * Resolves to the file name; rejects with an axios error whose body errorText() can read.
 */
export async function downloadFile(url, { params, method = 'get', data, fallbackName = 'download' } = {}) {
  try {
    const response = await api.request({ url: apiPath(url), method, params, data, responseType: 'blob' });
    const filename = filenameFrom(response.headers['content-disposition']) || fallbackName;
    saveBlob(response.data, filename);
    return filename;
  } catch (error) {
    throw await parseBlobError(error);
  }
}

/** Simplest path for a GET: a hidden link; the browser streams the file and names it from the server. */
export function downloadViaLink(url) {
  const link = document.createElement('a');
  link.href = url.startsWith('/') ? url : `/api/${url}`;
  link.download = '';
  link.style.display = 'none';
  document.body.appendChild(link);
  link.click();
  link.remove();
}
