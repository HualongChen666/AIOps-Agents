'use client'

import { ApprovalList } from '@/components/ApprovalList';

export default function ApprovalPage() {
  return (
    <main className="p-6 space-y-6 bg-gray-100 dark:bg-gray-900 min-h-screen">
      <section>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">
          HITL 审批中心
        </h1>
      </section>
      <ApprovalList />
    </main>
  );
}
