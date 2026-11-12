import { useEffect, useRef } from 'react';
import { getStamp } from './portalApi';

const FIRST = 4000;
const STEADY = 30000;
const LONGEST = 120000;

/*
 * The portal's poll (plan.md §8.20; L103; old `usePortalStamp`): first after 4 s, then every 30 s, backing off to two
 * minutes while nothing changes. When the form's stamp moves (the request changed, the link was submitted, closed or
 * given a new PIN) the page reads itself again and keeps what was typed. A refusal (gone, PIN) is the page's to show
 * on its next read, so the poll stops there. Writes nothing (the poll has its own rate, L110).
 */
export default function usePortalStamp(token, stamp, onMoved, enabled = true) {
  const seen = useRef(stamp);
  useEffect(() => {
    seen.current = stamp;
  }, [stamp]);

  useEffect(() => {
    if (!enabled) return undefined;
    let wait = FIRST;
    let timer = null;
    let stopped = false;
    const tick = async () => {
      try {
        const answer = await getStamp(token);
        if (answer.form_stamp !== seen.current) {
          seen.current = answer.form_stamp;
          onMoved();
          wait = STEADY;
        } else {
          wait = wait === FIRST ? STEADY : Math.min(wait * 2, LONGEST);
        }
      } catch (error) {
        if (error?.response?.status && error.response.status !== 429) {
          onMoved();
          return;
        }
        wait = Math.min(wait * 2, LONGEST);
      }
      if (!stopped) timer = setTimeout(tick, wait);
    };
    timer = setTimeout(tick, wait);
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [token, onMoved, enabled]);
}
