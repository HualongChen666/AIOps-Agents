'use client'

import React from 'react';

interface HistoryFiltersProps {
  onFilterChange?: (filters: HistoryFiltersState) => void;
}

interface HistoryFiltersState {
  queryType: 'all' | 'alerts' | 'repairs' | 'approvals';
  timeRange: string;
  severity: 'all' | 'P0' | 'P1' | 'P2' | 'P3';
  status: 'all' | 'success' | 'failure' | 'pending';
}

export const HistoryFilters: React.FC<HistoryFiltersProps> = ({ onFilterChange }) => {
  const [filters, setFilters] = React.useState<HistoryFiltersState>({
    queryType: 'all',
    timeRange: '24h',
    severity: 'all',
    status: 'all',
  });

  const handleFilterChange = (key: keyof HistoryFiltersState, value: string) => {
    const newFilters = { ...filters, [key]: value };
    setFilters(newFilters);
    onFilterChange?.(newFilters);
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <div className="flex flex-wrap gap-4 items-center">
        <div className="flex flex-col">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            查询类型
          </label>
          <select
            value={filters.queryType}
            onChange={(e) => handleFilterChange('queryType', e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
          >
            <option value="all">全部</option>
            <option value="alerts">告警</option>
            <option value="repairs">修复</option>
            <option value="approvals">审批</option>
          </select>
        </div>

        <div className="flex flex-col">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            时间范围
          </label>
          <select
            value={filters.timeRange}
            onChange={(e) => handleFilterChange('timeRange', e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
          >
            <option value="1h">最近1小时</option>
            <option value="24h">最近24小时</option>
            <option value="7d">最近7天</option>
            <option value="30d">最近30天</option>
            <option value="90d">最近90天</option>
          </select>
        </div>

        <div className="flex flex-col">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            严重程度
          </label>
          <select
            value={filters.severity}
            onChange={(e) => handleFilterChange('severity', e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
          >
            <option value="all">全部</option>
            <option value="P0">P0 - 严重</option>
            <option value="P1">P1 - 高</option>
            <option value="P2">P2 - 中</option>
            <option value="P3">P3 - 低</option>
          </select>
        </div>

        <div className="flex flex-col">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            状态
          </label>
          <select
            value={filters.status}
            onChange={(e) => handleFilterChange('status', e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
          >
            <option value="all">全部</option>
            <option value="success">成功</option>
            <option value="failure">失败</option>
            <option value="pending">待处理</option>
          </select>
        </div>

        <div className="ml-auto flex gap-2">
          <button className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors">
            重置
          </button>
          <button className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors">
            应用筛选
          </button>
        </div>
      </div>
    </div>
  );
};
