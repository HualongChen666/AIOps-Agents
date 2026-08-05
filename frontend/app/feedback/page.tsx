'use client'

import { useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';
import toast from 'react-hot-toast';

// Skeleton组件
const Skeleton = ({ className, variant = 'default' }: { className?: string; variant?: 'default' | 'text' | 'circular' }) => {
  const baseClasses = 'animate-pulse bg-gray-200';
  const variantClasses = {
    default: 'rounded',
    text: 'rounded h-4',
    circular: 'rounded-full',
  };

  return (
    <div className={`${baseClasses} ${variantClasses[variant]} ${className || ''}`} />
  );
};

// Empty组件
const Empty = ({
  title = '暂无数据',
  description = '这里什么都没有',
  action,
  icon
}: {
  title?: string;
  description?: string;
  action?: { label: string; onClick: () => void };
  icon?: ReactNode;
}) => {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      {icon || (
        <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
          <span className="text-3xl">📭</span>
        </div>
      )}
      <h3 className="text-lg font-medium text-gray-900 mb-2">{title}</h3>
      <p className="text-sm text-gray-500 mb-4 text-center">{description}</p>
      {action && (
        <Button onClick={action.onClick}>{action.label}</Button>
      )}
    </div>
  );
};

interface Stats {
  total: number;
  positive: number;
  negative: number;
  accuracy: number;
}

interface FeedbackRecord {
  feedback_id: string;
  feedback_type: 'positive' | 'negative';
  analysis_text?: string;
  query_text?: string;
  platform?: string;
  stage_name?: string;
  comment?: string;
  rich_context?: boolean;
  operator_ip?: string;
  created_at: string;
}

export default function FeedbackPage() {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<Stats>({ total: 0, positive: 0, negative: 0, accuracy: 0 });
  const [records, setRecords] = useState<FeedbackRecord[]>([]);

  const [feedbackType, setFeedbackType] = useState<'positive' | 'negative'>('positive');
  const [queryText, setQueryText] = useState('');
  const [analysisText, setAnalysisText] = useState('');
  const [stageName, setStageName] = useState('');
  const [platform, setPlatform] = useState('windows');
  const [comment, setComment] = useState('');
  const [richContext, setRichContext] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [statsRes, recentRes] = await Promise.all([
        api.get('/api/ai/feedback/stats'),
        api.get('/api/ai/feedback/recent'),
      ]);
      setStats(statsRes.data ?? { total: 0, positive: 0, negative: 0, accuracy: 0 });
      setRecords(recentRes.data?.records ?? []);
    } catch (err) {
      // api.ts 已经弹出了错误 toast
      console.error('加载反馈数据失败', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.post('/api/ai/feedback/submit', {
        feedback_type: feedbackType,
        analysis_text: analysisText,
        query_text: queryText,
        platform,
        stage_name: stageName,
        comment,
        rich_context: richContext,
      });
      toast.success('反馈已提交');
      setComment('');
      setAnalysisText('');
      setQueryText('');
      setStageName('');
      setRichContext(false);
      await loadData();
    } catch (err) {
      // api.ts 已经弹出了错误 toast
      console.error('提交反馈失败', err);
    } finally {
      setSubmitting(false);
    }
  };

  const formatTime = (iso: string) => {
    try {
      return new Date(iso).toLocaleString('zh-CN');
    } catch {
      return iso;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">AI 反馈闭环</h1>
      </div>

      {/* 统计概览 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm text-gray-500">总反馈数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-gray-900">
              {loading ? <Skeleton className="h-8 w-16" variant="text" /> : stats.total}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm text-gray-500">好评 / 👍</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-700">
              {loading ? <Skeleton className="h-8 w-16" variant="text" /> : stats.positive}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm text-gray-500">差评 / 👎</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-700">
              {loading ? <Skeleton className="h-8 w-16" variant="text" /> : stats.negative}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm text-gray-500">准确率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-700">
              {loading ? <Skeleton className="h-8 w-16" variant="text" /> : `${stats.accuracy}%`}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 提交反馈 */}
      <Card>
        <CardHeader>
          <CardTitle>提交 AI 反馈</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="flex gap-2">
              <Button
                type="button"
                variant={feedbackType === 'positive' ? 'default' : 'outline'}
                onClick={() => setFeedbackType('positive')}
              >
                👍 准确
              </Button>
              <Button
                type="button"
                variant={feedbackType === 'negative' ? 'default' : 'outline'}
                onClick={() => setFeedbackType('negative')}
              >
                👎 不准确
              </Button>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">用户问题 / Query</label>
              <input
                value={queryText}
                onChange={(e) => setQueryText(e.target.value)}
                className="w-full rounded border border-gray-300 p-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="请输入原始 query"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">AI 分析结果</label>
              <textarea
                value={analysisText}
                onChange={(e) => setAnalysisText(e.target.value)}
                rows={3}
                className="w-full rounded border border-gray-300 p-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="请输入 AI 分析结果原文"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">平台</label>
                <select
                  value={platform}
                  onChange={(e) => setPlatform(e.target.value)}
                  className="w-full rounded border border-gray-300 p-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="windows">Windows</option>
                  <option value="linux">Linux</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">流水线阶段</label>
                <input
                  value={stageName}
                  onChange={(e) => setStageName(e.target.value)}
                  className="w-full rounded border border-gray-300 p-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="阶段名称"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">附加评论（可选）</label>
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                rows={2}
                className="w-full rounded border border-gray-300 p-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="请补充说明"
              />
            </div>

            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={richContext}
                onChange={(e) => setRichContext(e.target.checked)}
                className="rounded border-gray-300"
              />
              启用富上下文 (M-1)
            </label>

            <Button type="submit" disabled={submitting || !analysisText.trim()}>
              {submitting ? '提交中...' : '提交反馈'}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* 最近反馈 */}
      <Card>
        <CardHeader>
          <CardTitle>最近反馈记录</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="p-4 border border-gray-200 rounded-lg space-y-2">
                  <Skeleton className="h-5 w-1/3" variant="text" />
                  <Skeleton className="h-4 w-2/3" variant="text" />
                  <Skeleton className="h-4 w-1/4" variant="text" />
                </div>
              ))}
            </div>
          ) : records.length === 0 ? (
            <Empty
              title="暂无反馈记录"
              description="还没有 AI 分析反馈，提交一条吧"
            />
          ) : (
            <div className="space-y-3">
              {records.map((item) => (
                <div key={item.feedback_id} className="p-4 border border-gray-200 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${item.feedback_type === 'positive'
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800'
                      }`}>
                      {item.feedback_type === 'positive' ? '👍 准确' : '👎 不准确'}
                    </span>
                    <span className="text-xs text-gray-500">{formatTime(item.created_at)}</span>
                  </div>
                  <p className="text-sm text-gray-900 mb-1">
                    <span className="font-medium">Query:</span> {item.query_text || '-'}
                  </p>
                  <p className="text-sm text-gray-600 mb-2 line-clamp-3">
                    <span className="font-medium">AI 分析:</span> {item.analysis_text || '-'}
                  </p>
                  <div className="flex flex-wrap gap-2 text-xs text-gray-500">
                    {item.platform && <span>平台: {item.platform}</span>}
                    {item.stage_name && <span>阶段: {item.stage_name}</span>}
                    {item.rich_context && <span>富上下文</span>}
                    {item.comment && <span className="w-full">评论: {item.comment}</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
