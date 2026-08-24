'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface DocumentIndex {
  id: string;
  name: string;
  type: 'text' | 'pdf' | 'html' | 'markdown';
  document_count: number;
  size_bytes: number;
  status: 'ready' | 'indexing' | 'error';
  created_at: string;
}

interface IndexingJob {
  id: string;
  index_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  error_message?: string;
}

export default function DocumentIndexPage() {
  const [indexes, setIndexes] = useState<DocumentIndex[]>([]);
  const [jobs, setJobs] = useState<IndexingJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newIndex, setNewIndex] = useState({ name: '', type: 'text' as const });

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [indexesRes, jobsRes] = await Promise.all([
        api.get('/api/ai/document-index/indexes'),
        api.get('/api/ai/document-index/jobs')
      ]);
      setIndexes(indexesRes.data.indexes || []);
      setJobs(jobsRes.data.jobs || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateIndex = async () => {
    try {
      await api.post('/api/ai/document-index/indexes', newIndex);
      setNewIndex({ name: '', type: 'text' });
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '创建索引失败');
    }
  };

  const handleReindex = async (indexId: string) => {
    try {
      await api.post(`/api/ai/document-index/indexes/${indexId}/reindex`);
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '重建索引失败');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="text-red-800">{error}</div>
        <Button onClick={fetchData} className="mt-2">重试</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">文档索引</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      {/* 索引列表 */}
      <Card>
        <CardHeader>
          <CardTitle>文档索引</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {indexes.map((index) => (
              <div key={index.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">{index.name}</h3>
                  <Badge variant={
                    index.status === 'ready' ? 'default' :
                    index.status === 'indexing' ? 'secondary' : 'destructive'
                  }>
                    {index.status}
                  </Badge>
                </div>
                <Badge variant="outline" className="mb-2">{index.type}</Badge>
                <div className="text-sm text-gray-600">文档数: {index.document_count}</div>
                <div className="text-sm text-gray-600">大小: {(index.size_bytes / 1024 / 1024).toFixed(2)} MB</div>
                <div className="text-xs text-gray-500 mt-1">
                  创建于: {new Date(index.created_at).toLocaleString()}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3 w-full"
                  onClick={() => handleReindex(index.id)}
                >
                  重建索引
                </Button>
              </div>
            ))}
          </div>

          {/* 创建新索引 */}
          <div className="mt-6 pt-6 border-t">
            <h3 className="font-semibold mb-4">创建新索引</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                placeholder="索引名称"
                value={newIndex.name}
                onChange={(e) => setNewIndex({ ...newIndex, name: e.target.value })}
              />
              <select
                className="border rounded px-3 py-2"
                value={newIndex.type}
                onChange={(e) => setNewIndex({ ...newIndex, type: e.target.value as any })}
              >
                <option value="text">文本</option>
                <option value="pdf">PDF</option>
                <option value="html">HTML</option>
                <option value="markdown">Markdown</option>
              </select>
            </div>
            <Button onClick={handleCreateIndex} className="mt-4">创建索引</Button>
          </div>
        </CardContent>
      </Card>

      {/* 索引任务 */}
      <Card>
        <CardHeader>
          <CardTitle>索引任务</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {jobs.map((job) => (
              <div key={job.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <Badge variant={
                    job.status === 'completed' ? 'default' :
                    job.status === 'processing' ? 'secondary' :
                    job.status === 'failed' ? 'destructive' : 'outline'
                  }>
                    {job.status}
                  </Badge>
                  <span className="text-sm text-gray-600">{job.progress.toFixed(1)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full transition-all"
                    style={{ width: `${job.progress}%` }}
                  />
                </div>
                {job.error_message && (
                  <div className="text-sm text-red-600 mt-2">{job.error_message}</div>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
