'use client'

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';

interface HistoryRecord {
  id: string;
  type: 'alert' | 'repair' | 'approval';
  title: string;
  description: string;
  severity?: string;
  status: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

export const HistorySearch: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRecord, setSelectedRecord] = useState<HistoryRecord | null>(null);

  const { data, isLoading, error } = useQuery<HistoryRecord[]>({
    queryKey: ['history'],
    queryFn: async () => {
      const resp = await api.get<HistoryRecord[]>('/api/v1/history');
      return resp.data;
    },
    enabled: true,
  });

  const filteredData = data?.filter(record =>
    record.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    record.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'alert':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      case 'repair':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'approval':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
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
        <div className="text-center text-red-500">获取历史记录失败</div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <input
          type="text"
          placeholder="搜索历史记录..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
        />
      </div>

      <div className="divide-y divide-gray-200 dark:divide-gray-700 max-h-96 overflow-y-auto">
        {filteredData && filteredData.length > 0 ? (
          filteredData.map((record) => (
            <div
              key={record.id}
              onClick={() => setSelectedRecord(record)}
              className="p-4 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${getTypeColor(record.type)}`}>
                      {record.type.toUpperCase()}
                    </span>
                    {record.severity && (
                      <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200">
                        {record.severity}
                      </span>
                    )}
                  </div>
                  <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-1">
                    {record.title}
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                    {record.description}
                  </p>
                  <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                    {new Date(record.timestamp).toLocaleString()}
                  </div>
                </div>
                <span
                  className={`px-2 py-1 text-xs font-medium rounded ${
                    record.status === 'success'
                      ? 'bg-green-100 text-green-800'
                      : record.status === 'failure'
                      ? 'bg-red-100 text-red-800'
                      : 'bg-yellow-100 text-yellow-800'
                  }`}
                >
                  {record.status}
                </span>
              </div>
            </div>
          ))
        ) : (
          <div className="p-6 text-center text-gray-500 dark:text-gray-400">
            {searchQuery ? '未找到匹配的历史记录' : '暂无历史记录'}
          </div>
        )}
      </div>

      {selectedRecord && (
        <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              记录详情
            </h3>
            <button
              onClick={() => setSelectedRecord(null)}
              className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            >
              ✕
            </button>
          </div>
          <div className="space-y-2 text-sm">
            <div>
              <span className="font-medium text-gray-700 dark:text-gray-300">ID:</span>
              <span className="ml-2 text-gray-900 dark:text-gray-100">{selectedRecord.id}</span>
            </div>
            <div>
              <span className="font-medium text-gray-700 dark:text-gray-300">类型:</span>
              <span className="ml-2 text-gray-900 dark:text-gray-100">{selectedRecord.type}</span>
            </div>
            <div>
              <span className="font-medium text-gray-700 dark:text-gray-300">标题:</span>
              <span className="ml-2 text-gray-900 dark:text-gray-100">{selectedRecord.title}</span>
            </div>
            <div>
              <span className="font-medium text-gray-700 dark:text-gray-300">描述:</span>
              <p className="mt-1 text-gray-600 dark:text-gray-400">{selectedRecord.description}</p>
            </div>
            <div>
              <span className="font-medium text-gray-700 dark:text-gray-300">时间:</span>
              <span className="ml-2 text-gray-900 dark:text-gray-100">
                {new Date(selectedRecord.timestamp).toLocaleString()}
              </span>
            </div>
            {selectedRecord.metadata && (
              <div>
                <span className="font-medium text-gray-700 dark:text-gray-300">元数据:</span>
                <pre className="mt-1 p-2 bg-gray-100 dark:bg-gray-800 rounded text-xs overflow-auto">
                  {JSON.stringify(selectedRecord.metadata, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
