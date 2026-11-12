import { describe, expect, it, vi } from 'vitest';
import { createWriteQueue } from './writeQueue';

// A send whose answers the test releases one at a time.
function fakeServer() {
  const calls = [];
  const send = vi.fn(
    (cell, value, expect) =>
      new Promise((resolve, reject) => {
        calls.push({ cell, value, expect, resolve, reject });
      }),
  );
  return { calls, send };
}

const tick = () => new Promise((resolve) => setTimeout(resolve, 0));

describe('F71 the per-cell write queue', () => {
  it('sends one request per cell at a time, and the latest value wins', async () => {
    const server = fakeServer();
    const queue = createWriteQueue({ send: server.send });
    const first = queue.enqueue('41|rate_ee', '600', '512.34');
    const second = queue.enqueue('41|rate_ee', '610', '600');
    const third = queue.enqueue('41|rate_ee', '620', '610');
    await tick();
    expect(server.calls).toHaveLength(1);
    expect(server.calls[0]).toMatchObject({ value: '600', expect: '512.34' });
    expect(await second).toBeNull(); // replaced before it was sent
    server.calls[0].resolve('600.00');
    expect(await first).toEqual({ before: '512.34', after: '600.00' });
    await tick();
    expect(server.calls).toHaveLength(2);
    // The queued write expects what the server stored for the one before it.
    expect(server.calls[1]).toMatchObject({ value: '620', expect: '600.00' });
    server.calls[1].resolve('620.00');
    expect(await third).toEqual({ before: '600.00', after: '620.00' });
  });

  it('writes different cells side by side', async () => {
    const server = fakeServer();
    const queue = createWriteQueue({ send: server.send });
    queue.enqueue('41|rate_ee', '1', '');
    queue.enqueue('41|rate_es', '2', '');
    queue.enqueue('42|rate_ee', '3', '');
    await tick();
    expect(server.calls.map((call) => call.cell)).toEqual(['41|rate_ee', '41|rate_es', '42|rate_ee']);
  });

  it('applies a cell results in the order sent', async () => {
    const server = fakeServer();
    const order = [];
    const queue = createWriteQueue({ send: server.send });
    queue.enqueue('41|rate_ee', 'a', '').then((r) => order.push(r.after));
    await tick();
    const later = queue.enqueue('41|rate_ee', 'b', 'a').then((r) => order.push(r.after));
    server.calls[0].resolve('A');
    await tick();
    server.calls[1].resolve('B');
    await later;
    expect(order).toEqual(['A', 'B']);
  });

  it('on a failure restores the last saved value and drops what waited behind it', async () => {
    const server = fakeServer();
    const onFailed = vi.fn();
    const queue = createWriteQueue({ send: server.send, onFailed });
    const first = queue.enqueue('41|rate_ee', 'abc', '512.34');
    const waiting = queue.enqueue('41|rate_ee', 'abcd', 'abc');
    await tick();
    const error = new Error('Rate — EE: enter a number');
    server.calls[0].reject(error);
    await expect(first).rejects.toBe(error);
    expect(await waiting).toBeNull();
    expect(onFailed).toHaveBeenCalledWith('41|rate_ee', error, '512.34');
    await tick();
    expect(server.calls).toHaveLength(1);
    expect(queue.busy('41|rate_ee')).toBe(false);
  });

  it('calls onIdle once per burst, when every cell has settled', async () => {
    const server = fakeServer();
    const onIdle = vi.fn();
    const queue = createWriteQueue({ send: server.send, onIdle });
    queue.enqueue('41|rate_ee', '1', '');
    queue.enqueue('42|rate_ee', '2', '');
    await tick();
    server.calls[0].resolve('1');
    await tick();
    expect(onIdle).not.toHaveBeenCalled();
    server.calls[1].resolve('2');
    await queue.settle();
    await tick();
    expect(onIdle).toHaveBeenCalledTimes(1);
    expect(queue.busy('41|rate_ee')).toBe(false);
  });

  it('settles at once when nothing is in flight', async () => {
    const queue = createWriteQueue({ send: vi.fn() });
    await expect(queue.settle()).resolves.toBeUndefined();
  });
});
