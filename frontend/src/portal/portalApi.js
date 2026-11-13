/*
 * The client portal's own axios instance (plan.md §3.9, §7.14; L.6 `portalApi`). No session, no CSRF: a client's
 * browser holds no Django session. Once a PIN is proved, the server's verification token (`X-Link-Verification`) is
 * kept in sessionStorage, one per link, sent with every request and replaced by the fresh one each answer carries
 * (an hour idle under an eight-hour ceiling). Nothing about the link goes in localStorage.
 */
import axios from 'axios';
import { saveBlob, filenameFrom } from '../lib/download';

const HEADER = 'X-Link-Verification';
const portal = axios.create({ baseURL: '/api/portal/' });

const keyOf = (token) => `vantage.portal.verify.${token}`;

function stored(token) {
  try {
    return sessionStorage.getItem(keyOf(token)) || '';
  } catch {
    return '';
  }
}

function keep(token, value) {
  try {
    if (value) sessionStorage.setItem(keyOf(token), value);
  } catch {
    /* blocked storage: the PIN is asked again on the next load */
  }
}

/** One request on a link: the proof rides along, and the fresh one it gets back is kept. */
async function call(token, config) {
  const proof = stored(token);
  const headers = { ...(config.headers || {}), ...(proof ? { [HEADER]: proof } : {}) };
  const response = await portal.request({ ...config, headers });
  keep(token, response.headers[HEADER.toLowerCase()]);
  return response;
}

const door = (token, path = '') => `${encodeURIComponent(token)}/${path}`;

export async function getPage(token) {
  return (await call(token, { url: door(token), method: 'get' })).data;
}

export async function verifyPin(token, pin) {
  return (await call(token, { url: door(token, 'verify/'), method: 'post', data: { pin } })).data;
}

export async function saveAnswers(token, answers) {
  return (await call(token, { url: door(token, 'save/'), method: 'post', data: { answers } })).data;
}

export async function submitAnswers(token, answers) {
  return (await call(token, { url: door(token, 'submit/'), method: 'post', data: { answers } })).data;
}

export async function uploadFile(token, slot, file) {
  const form = new FormData();
  form.append('slot', slot);
  form.append('file', file);
  return (await call(token, { url: door(token, 'files/'), method: 'post', data: form })).data;
}

export async function addPeople(token, people) {
  return (await call(token, { url: door(token, 'people/'), method: 'post', data: { people } })).data;
}

export async function signBor(token, name) {
  return (await call(token, { url: door(token, 'sign/'), method: 'post', data: { name } })).data;
}

/** POST questions/ {questions: [{ref, text}]} → {follow_ups} (L101; slice 56). 400 {questions: [sentence]}. */
export async function askQuestions(token, questions) {
  return (await call(token, { url: door(token, 'questions/'), method: 'post', data: { questions } })).data;
}

/** POST seen/ → {seen_at}: the page's last look at its follow-ups (L103; slice 56). */
export async function postSeen(token) {
  return (await call(token, { url: door(token, 'seen/'), method: 'post', data: {} })).data;
}

export async function getStamp(token) {
  return (await call(token, { url: door(token, 'stamp/'), method: 'get' })).data;
}

/** The blank census template (B3), saved under the server's name. */
export async function downloadTemplate(token) {
  const response = await call(token, { url: door(token, 'census-template/'), method: 'get', responseType: 'blob' });
  saveBlob(response.data, filenameFrom(response.headers['content-disposition']) || 'Census template.xlsx');
}

// ---- questionnaires (slice 58; G84, G87, G93) ----------------------------------------------------------------------

const formDoor = (token, key, path = '') => door(token, `questionnaires/${encodeURIComponent(key)}/${path}`);

/** GET questionnaires/{form}/spec/?v= → the form as this link asks it (the one answer the browser may keep). */
export async function getFormSpec(token, key, version) {
  return (await call(token, { url: formDoor(token, key, 'spec/'), method: 'get', params: { v: version } })).data;
}

/** POST questionnaires/{form}/rows/ {block} → 201 {row_id, state, link}. */
export async function addFormRow(token, key, block) {
  return (await call(token, { url: formDoor(token, key, 'rows/'), method: 'post', data: { block } })).data;
}

/** DELETE questionnaires/{form}/rows/{block}/{row_id}/ → {state, link}. */
export async function removeFormRow(token, key, block, rowId) {
  const url = formDoor(token, key, `rows/${encodeURIComponent(block)}/${rowId}/`);
  return (await call(token, { url, method: 'delete' })).data;
}

/** POST questionnaires/{form}/sign/ {name, sign_anyway} → {questionnaire, link}; 409 {detail, incomplete}. */
export async function signForm(token, key, name, signAnyway = false) {
  const data = { name, sign_anyway: signAnyway };
  return (await call(token, { url: formDoor(token, key, 'sign/'), method: 'post', data })).data;
}

/** The carrier's blank PDF: its bytes to show on the page, or saved under the server's name. */
export async function getFormBlank(token, key, { save = false } = {}) {
  const response = await call(token, {
    url: formDoor(token, key, 'blank/'),
    method: 'get',
    responseType: save ? 'blob' : 'arraybuffer',
    params: save ? {} : { inline: 1 },
  });
  if (!save) return new Uint8Array(response.data);
  saveBlob(response.data, filenameFrom(response.headers['content-disposition']) || `${key}-blank.pdf`);
  return null;
}

/** The agency's contact for "This link has moved" (L136). It sends no token. */
export async function getMoved() {
  return (await portal.get('moved/')).data;
}

export function statusOf(error) {
  return error?.response?.status ?? null;
}

/** The server's sentence for a refusal, or ''. */
export function detailOf(error) {
  const data = error?.response?.data;
  return data && typeof data.detail === 'string' ? data.detail : '';
}
