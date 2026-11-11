/** Joins class names, skipping falsy values. */
export default function cx(...names) {
  return names.filter(Boolean).join(' ');
}
