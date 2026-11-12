// Copying is the send (OQ82): nothing is mailed, so a person copies a link and pastes it into their own email.
// Returns true once the text is on the clipboard; false when the browser refused (the caller then shows the text to
// copy by hand, as the old card's toast asked).

export default async function copyText(text) {
  if (!text) return false;
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}
