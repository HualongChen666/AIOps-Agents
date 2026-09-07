// Utility to split large arrays of requests into batches to avoid overloading the backend.
// Each batch will be processed sequentially, but requests inside a batch run in parallel via Promise.all.
// Usage example: await batchRequests(items, 50, (chunk) => api.fetchItems(chunk));

export async function batchRequests<T, R>(
  items: T[],
  batchSize: number,
  handler: (batch: T[]) => Promise<R[]>
): Promise<R[]> {
  const results: R[] = [];
  for (let i = 0; i < items.length; i += batchSize) {
    const batch = items.slice(i, i + batchSize);
    // eslint-disable-next-line no-await-in-loop – intentional sequential batching
    const batchResult = await handler(batch);
    results.push(...batchResult);
  }
  return results;
}
