import { batchRequests } from '@/lib/batchRequest';

describe('lib/batchRequest', () => {
  it('returns an empty array for empty input without calling the handler', async () => {
    const handler = jest.fn(async (batch: number[]) => batch.map((n) => n * 2));
    await expect(batchRequests([], 10, handler)).resolves.toEqual([]);
    expect(handler).not.toHaveBeenCalled();
  });

  it('passes the whole array through when it fits in one batch', async () => {
    const handler = jest.fn(async (batch: number[]) => batch.map((n) => n * 2));
    const result = await batchRequests([1, 2, 3], 10, handler);
    expect(result).toEqual([2, 4, 6]);
    expect(handler).toHaveBeenCalledTimes(1);
    expect(handler).toHaveBeenCalledWith([1, 2, 3]);
  });

  it('splits the input into sequential chunks of batchSize', async () => {
    const calls: number[][] = [];
    const handler = jest.fn(async (batch: number[]) => {
      calls.push(batch);
      return batch.map((n) => n + 1);
    });

    const result = await batchRequests([1, 2, 3, 4, 5], 2, handler);

    expect(calls).toEqual([[1, 2], [3, 4], [5]]);
    expect(result).toEqual([2, 3, 4, 5, 6]);
    expect(handler).toHaveBeenCalledTimes(3);
  });

  it('processes batches sequentially (in order) and concatenates results in order', async () => {
    const order: number[] = [];
    const handler = async (batch: number[]): Promise<string[]> => {
      order.push(batch[0]);
      await new Promise((resolve) => setTimeout(resolve, 0));
      return batch.map((n) => `r${n}`);
    };

    const result = await batchRequests([1, 2, 3, 4], 2, handler);
    expect(order).toEqual([1, 3]);
    expect(result).toEqual(['r1', 'r2', 'r3', 'r4']);
  });

  it('propagates a handler rejection', async () => {
    const handler = jest.fn(async () => {
      throw new Error('boom');
    });
    await expect(batchRequests([1, 2], 1, handler)).rejects.toThrow('boom');
  });

  it('handles a batch size larger than the array', async () => {
    const handler = jest.fn(async (batch: number[]) => batch);
    const result = await batchRequests([1, 2, 3], 100, handler);
    expect(result).toEqual([1, 2, 3]);
    expect(handler).toHaveBeenCalledTimes(1);
  });
});
