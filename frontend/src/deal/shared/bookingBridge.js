// The booking summary's bridge (plan.md §8.13; H35): module state shared by tab folders that never import each other.
// The Advisor's board (and the Proposal's presented grid, which uses the same actions) opens it when a Mark sold makes
// the deal Sold for the first time; any "Booked · view" link opens it again. The deal page mounts the one modal
// (pages/DealPage/BookingSlot.jsx), which shows whichever deal was asked for while that deal is on screen.

let openFor = null; // the deal id whose summary is open, or null
const listeners = new Set();

function notify() {
  listeners.forEach((listener) => listener());
}

/** Open the booking summary of `dealId`. */
export function open(dealId) {
  openFor = Number(dealId);
  notify();
}

export function close() {
  openFor = null;
  notify();
}

/** The deal id whose summary is open, or null (useSyncExternalStore's snapshot). */
export function current() {
  return openFor;
}

export function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
