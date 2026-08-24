'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface Feedback {
  id: string;
  type: 'positive' | 'negative' | 'suggestion';
  content: string;
  rating: number;
  category: string;
  created_at: string;
  status: 'pending' | 'reviewed' | 'implemented';
}

interface FeedbackStats {
  total: number;
  positive: number;
  negative: number;
  suggestions: number;
  avg_rating: number;
}

export default function AIFeedbackPage() {
  const [feedbacks, setFeedbacks] = useState<Feedback[]>([]);
  const [stats, setStats] = useState<FeedbackStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newFeedback, setNewFeedback] = useState({
    type: 'suggestion' as const,
    content: '',
    rating: 5,
    category: 'general'
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [feedbacksRes, statsRes] = await Promise.all([
        api.get('/api/ai/ai-feedback/feedbacks'),
        api.get('/api/ai/ai-feedback/stats')
      ]);
      setFeedbacks(feedbacksRes.data.feedbacks || []);
      setStats(statsRes.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitFeedback = async () => {
    try {
      await api.post('/api/ai/ai-feedback/feedbacks', newFeedback);
      setNewFeedback({ type: 'suggestion', content: '', rating: 5, category: 'general' });
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '提交反馈失败');
    }
  };

  const handleUpdateStatus = async (id: string, status: string) => {
    try {
      await api.patch(`/api/ai/ai-feedback/feedbacks/${id}`, { status });
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '更新状态失败');
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
        <h1 className="text-3xl font-bold text-gray-900">AI反馈收集</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      {/* 统计信息 */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader>
              <CardTitle>总反馈数</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{stats.total}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>正面反馈</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-green-600">{stats.positive}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>负面反馈</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-red-600">{stats.negative}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>平均评分</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{stats.avg_rating.toFixed(1)}</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 提交反馈 */}
      <Card>
        <CardHeader>
          <CardTitle>提交反馈</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <select
                className="border rounded px-3 py-2"
                value={newFeedback.type}
                onChange={(e) => setNewFeedback({ ...newFeedback, type: e.target.value as any })}
              >
                <option value="positive">正面反馈</option>
                <option value="negative">负面反馈</option>
                <option value="suggestion">建议</option>
              </select>
              <Input
                placeholder="类别"
                value={newFeedback.category}
                onChange={(e) => setNewFeedback({ ...newFeedback, category: e.target.value })}
              />
            </div>
            <Input
              type="number"
              min="1"
              max="5"
              placeholder="评分 (1-5)"
              value={newFeedback.rating}
              onChange={(e) => setNewFeedback({ ...newFeedback, rating: parseInt(e.target.value) || 5 })}
            />
            <textarea
              placeholder="反馈内容..."
              value={newFeedback.content}
              onChange={(e) => setNewFeedback({ ...newFeedback, content: e.target.value })}
              className="w-full border rounded p-2 h-24"
            />
            <Button onClick={handleSubmitFeedback}>提交反馈</Button>
          </div>
        </CardContent>
      </Card>

      {/* 反馈列表 */}
      <Card>
        <CardHeader>
          <CardTitle>反馈列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {feedbacks.map((feedback) => (
              <div key={feedback.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Badge variant={
                      feedback.type === 'positive' ? 'default' :
                      feedback.type === 'negative' ? 'destructive' : 'secondary'
                    }>
                      {feedback.type}
                    </Badge>
                    <Badge variant="outline">{feedback.category}</Badge>
                    <Badge variant="outline">评分: {feedback.rating}</Badge>
                  </div>
                  <Badge variant={
                    feedback.status === 'implemented' ? 'default' :
                    feedback.status === 'reviewed' ? 'secondary' : 'outline'
                  }>
                    {feedback.status}
                  </Badge>
                </div>
                <p className="text-sm text-gray-700 mb-2">{feedback.content}</p>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500">
                    {new Date(feedback.created_at).toLocaleString()}
                  </span>
                  {feedback.status === 'pending' && (
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleUpdateStatus(feedback.id, 'reviewed')}
                      >
                        标记已审阅
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleUpdateStatus(feedback.id, 'implemented')}
                      >
                        标记已实施
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
