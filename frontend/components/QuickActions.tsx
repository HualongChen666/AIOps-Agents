'use client'

import React from 'react';
import { useRouter } from 'next/navigation';

export const QuickActions: React.FC = () => {
  const router = useRouter();

  const actions = [
    { label: '新建告警规则', href: '/alerts', icon: '🔔' },
    { label: '查看拓扑', href: '/topology', icon: '🔗' },
    { label: '审批中心', href: '/approval', icon: '✅' },
    { label: 'RAG搜索', href: '/history', icon: '🔍' },
  ];

  // A failed navigation (blocked route, router not ready, …) must not crash the
  // dashboard — surface it and let the user retry.
  const navigate = (href: string) => {
    try {
      router.push(href);
    } catch (err) {
      console.error('Navigation failed:', err);
    }
  };

  return (
    <div className="flex gap-2">
      {actions.map((action) => (
        <button
          key={action.href}
          onClick={() => navigate(action.href)}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium transition-colors flex items-center gap-2"
        >
          <span>{action.icon}</span>
          <span>{action.label}</span>
        </button>
      ))}
    </div>
  );
};
