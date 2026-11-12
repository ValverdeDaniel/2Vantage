import { describe, expect, it } from 'vitest';
import * as bridge from './bookingBridge';

describe('bookingBridge (H35)', () => {
  it('H35_opens_the_summary_of_one_deal_and_tells_its_listeners', () => {
    const seen = [];
    const stop = bridge.subscribe(() => seen.push(bridge.current()));
    bridge.open('12');
    expect(bridge.current()).toBe(12);
    bridge.close();
    expect(bridge.current()).toBeNull();
    stop();
    bridge.open(5);
    expect(seen).toEqual([12, null]);
    bridge.close();
  });
});
