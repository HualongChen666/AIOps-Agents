'use client'

import React, { useState, useEffect } from 'react';
import { ApprovalList } from '@/components/ApprovalList';
import { ApprovalFilters } from '@/components/ApprovalFilters';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';

export default function ApprovalPage() {
  // 🔧 P1-4: State Management
  const { isLoading, error, setLoading, setError } = useLoadingState(false);
  const { success, error: showError } = useToast();
  const [approvals, setApprovals] = useState<any[]>([]);
  const [filter, setFilter] = useState({ status: 'all', priority: 'all' });

  const handleApprove = async (id: string) => {
    try {
      await fetch(`/api/v1/approval/${id}/approve`, { method: 'POST' });
      success("Approval completed successfully");
      // Refresh list
      loadApprovals();
    } catch (err) {
      showError("Failed to approve");
    }
  };

  const handleReject = async (id: string) => {
    try {
      await fetch(`/api/v1/approval/${id}/reject`, { method: 'POST' });
      success("Approval rejected successfully");
      // Refresh list
      loadApprovals();
    } catch (err) {
      showError("Failed to reject");
    }
  };

  const loadApprovals = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/v1/approval?status=${filter.status}&priority=${filter.priority}`);
      const data = await res.json();
      setApprovals(data);
      setLoading(false);
    } catch (err) {
      setError(err);
      setLoading(false);
    }
  };

  useEffect(() => {
    loadApprovals();
  }, [filter]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-600 dark:text-gray-400">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-red-600 dark:text-red-400">Error: {error.message}</div>
      </div>
    );
  }

  return (
    <main className="p-6 space-y-6 bg-gray-100 dark:bg-gray-900 min-h-screen">
      <section>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">
          HITL 审批中心
        </h1>
        <ApprovalFilters filter={filter} onFilterChange={setFilter} />
      </section>
      
      <section>
        <ApprovalList 
          approvals={approvals}
          onApprove={handleApprove}
          onReject={handleReject}
        />
      </section>
    </main>
  );
}
