'use client'

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';

interface PendingApproval {
  id: string;
  alert_id: string;
  alert_json: string;
  rule_name: string;
  script_key: string;
  proposal: string;
  status: 'pending' | 'approved' | 'rejected';
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  submitted_at: string;
  host?: string;
  platform?: string;
}

export const ApprovalList: React.FC = () => {
  const { data, isLoading, error, refetch } = useQuery<PendingApproval[]>({
    queryKey: ['approvals'],
    queryFn: async () => {
      const resp = await api.get<{ items?: PendingApproval[] }>('/api/v1/approvals/pending');
      return resp.data.items || [];
    },
    refetchInterval: 30_000,
  });

  const handleApprove = async (id: string) => {
    try {
      await api.patch(`/api/v1/approvals/${id}`);
      refetch();
    } catch (error) {
      console.error('Failed to approve:', error);
    }
  };

  const handleReject = async (id: string, reason: string) => {
    try {
      await api.post('/api/v1/approvals/reject', { alert_id: id, reason });
      refetch();
    } catch (error) {
      console.error('Failed to reject:', error);
    }
  };

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'low':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
      case 'high':
        return 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200';
      case 'critical':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200';
    }
  };

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="text-center text-gray-500">加载中…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="text-center text-red-500">获取审批列表失败</div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="text-center text-gray-500">暂无待审批项</div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
      <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
        <thead className="bg-gray-50 dark:bg-gray-900">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              告警ID
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              规则名称
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              提案
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              风险等级
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              提交时间
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              操作
            </th>
          </tr>
        </thead>
        <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
          {data.map((approval) => (
            <tr key={approval.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                {approval.alert_id}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                {approval.rule_name}
              </td>
              <td className="px-6 py-4 text-sm text-gray-700 dark:text-gray-300 max-w-xs truncate">
                {approval.proposal}
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getRiskColor(approval.risk_level)}`}>
                  {approval.risk_level.toUpperCase()}
                </span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                {new Date(approval.submitted_at).toLocaleString()}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                <div className="flex gap-2">
                  <button
                    onClick={() => handleApprove(approval.id)}
                    className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 transition-colors"
                  >
                    批准
                  </button>
                  <button
                    onClick={() => handleReject(approval.id, '用户拒绝')}
                    className="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
                  >
                    拒绝
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
