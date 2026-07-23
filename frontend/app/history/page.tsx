import React from 'react';
import { HistorySearch } from '@/components/HistorySearch';
import { HistoryFilters } from '@/components/HistoryFilters';

export default function HistoryPage() {
  return (
    <main className="p-6 space-y-6 bg-gray-100 dark:bg-gray-900 min-h-screen">
      <section>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">
          RAG 历史搜索
        </h1>
        <HistoryFilters />
      </section>
      
      <section>
        <HistorySearch />
      </section>
    </main>
  );
}
