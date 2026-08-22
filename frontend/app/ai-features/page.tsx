'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { EnhancedModal } from '@/components/ui/EnhancedModal';
import { DataTable } from '@/components/ui/DataTable';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { KpiCard } from '@/components/ui/KpiCard';
import { TrendChart } from '@/components/charts/TrendChart';
import { Brain, RefreshCw, Zap, TrendingUp, MessageSquare, Lightbulb, BookOpen, Plus } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface AIPrediction {
  type: string;
  predicted_values: number[];
  confidence: number;
  model_used: string;
  prediction_timestamp: string;
  metadata: Record<string, any>;
}

interface AIAnomaly {
  metric: string;
  value: number;
  is_anomaly: boolean;
  confidence: number;
}

interface AIConversation {
  conversation_id: string;
  user_id: string;
  user_input: string;
  ai_response: string;
  timestamp: string;
}

export default function AIFeaturesPage() {
  const [activeTab, setActiveTab] = useState<'prediction' | 'anomaly' | 'conversation' | 'learning'>('prediction');
  const [showPredictionModal, setShowPredictionModal] = useState(false);
  const [showConversationModal, setShowConversationModal] = useState(false);
  const [predictionData, setPredictionData] = useState({
    historical_data: [],
    prediction_horizon: 24,
  });
  const [conversationData, setConversationData] = useState({
    user_input: '',
    conversation_id: '',
    user_id: 'current_user',
  });

  const queryClient = useQueryClient();

  // 🔧 获取AI能力状态
  const { data: aiStatusData, isLoading: statusLoading, refetch: refetchStatus } = useQuery<{ available: boolean; capabilities: string[] }>({
    queryKey: ['ai-status'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/ai-advanced/status');
      return resp.data;
    },
    refetchInterval: 60000, // 60秒刷新
  });

  // 🔧 时序预测
  const predictTimeSeriesMutation = useMutation({
    mutationFn: async (data: typeof predictionData) => {
      const resp = await api.post('/api/v1/ai-advanced/predict/time-series', data);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-predictions'] });
      setShowPredictionModal(false);
      showSuccess('时序预测成功');
    },
    onError: () => {
      showError('时序预测失败');
    },
  });

  // 🔧 自然语言交互
  const naturalLanguageMutation = useMutation({
    mutationFn: async (data: typeof conversationData) => {
      const resp = await api.post('/api/v1/ai-advanced/natural-language', data);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-conversations'] });
      setShowConversationModal(false);
      setConversationData({ ...conversationData, user_input: '' });
      showSuccess('AI响应成功');
    },
    onError: () => {
      showError('AI响应失败');
    },
  });

  // 🔧 P1 Integration: Use enhanced loading state
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(statusLoading);

  // 🔧 P1 Integration: Use toast notifications
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // 🔧 P1 Integration: Handle errors with toast
  useEffect(() => {
    if (pageError) {
      showError('Failed to load AI status');
      setPageError(pageError as Error);
    }
  }, [pageError, showError, setPageError]);

  const aiStatus = aiStatusData || { available: false, capabilities: [] };

  const handleTimeSeriesPrediction = () => {
    predictTimeSeriesMutation.mutate(predictionData);
  };

  const handleNaturalLanguage = () => {
    naturalLanguageMutation.mutate(conversationData);
  };

  const handleRefresh = () => {
    refetchStatus();
  };

  // 🔧 P1 Integration: Use enhanced loading and empty states
  if (pageLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (pageError) {
    return (
      <ErrorBoundary fallback={
        <EmptyState
          title="加载失败"
          description="无法加载AI功能数据，请稍后重试"
          action={<Button onClick={handleRefresh}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={handleRefresh}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Brain className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">AI功能</h1>
            <p className="text-sm text-gray-500">高级AI能力和智能分析</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleRefresh} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">AI状态</CardTitle>
          </CardHeader>
          <CardContent>
            <p className={`text-3xl font-bold ${aiStatus.available ? 'text-green-600' : 'text-gray-600'}`}>
              {aiStatus.available ? '可用' : '不可用'}
            </p>
            <p className="text-sm text-gray-500 mt-1">AI引擎状态</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">能力数量</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">{aiStatus.capabilities.length}</p>
            <p className="text-sm text-gray-500 mt-1">可用AI能力</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">模型类型</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-purple-600">6</p>
            <p className="text-sm text-gray-500 mt-1">AI模型数量</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        <Button
          variant={activeTab === 'prediction' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('prediction')}
        >
          <TrendingUp className="h-4 w-4 mr-2" />
          时序预测
        </Button>
        <Button
          variant={activeTab === 'anomaly' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('anomaly')}
        >
          <Zap className="h-4 w-4 mr-2" />
          异常检测
        </Button>
        <Button
          variant={activeTab === 'conversation' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('conversation')}
        >
          <MessageSquare className="h-4 w-4 mr-2" />
          自然语言
        </Button>
        <Button
          variant={activeTab === 'learning' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('learning')}
        >
          <BookOpen className="h-4 w-4 mr-2" />
          知识学习
        </Button>
      </div>

      {/* Prediction Tab */}
      {activeTab === 'prediction' && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                时序预测
              </CardTitle>
              <Button size="sm" onClick={() => setShowPredictionModal(true)}>
                <Plus className="h-4 w-4 mr-1" />
                创建预测
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <EmptyState
              title="时序预测功能"
              description="基于历史数据进行时序预测分析"
              action={<Button onClick={() => setShowPredictionModal(true)}>创建第一个预测</Button>}
            />
          </CardContent>
        </Card>
      )}

      {/* Anomaly Tab */}
      {activeTab === 'anomaly' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5" />
              异常检测
            </CardTitle>
          </CardHeader>
          <CardContent>
            <EmptyState
              title="异常检测功能"
              description="基于统计分析的异常预测和检测"
            />
          </CardContent>
        </Card>
      )}

      {/* Conversation Tab */}
      {activeTab === 'conversation' && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <MessageSquare className="h-5 w-5" />
                自然语言交互
              </CardTitle>
              <Button size="sm" onClick={() => setShowConversationModal(true)}>
                <Plus className="h-4 w-4 mr-1" />
                发起对话
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <EmptyState
              title="自然语言交互"
              description="与AI进行自然语言对话和指令交互"
              action={<Button onClick={() => setShowConversationModal(true)}>发起对话</Button>}
            />
          </CardContent>
        </Card>
      )}

      {/* Learning Tab */}
      {activeTab === 'learning' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="h-5 w-5" />
              知识学习
            </CardTitle>
          </CardHeader>
          <CardContent>
            <EmptyState
              title="知识学习功能"
              description="持续学习和知识积累"
            />
          </CardContent>
        </Card>
      )}

      {/* Time Series Prediction Modal */}
      <EnhancedModal
        open={showPredictionModal}
        onOpenChange={setShowPredictionModal}
        title="时序预测"
        size="md"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">预测时长（小时）</label>
            <select
              value={String(predictionData.prediction_horizon)}
              onChange={(e) => setPredictionData({ ...predictionData, prediction_horizon: Number(e.target.value) })}
              className="w-full px-3 py-2 border rounded-md bg-white"
            >
              <option value="24">24小时</option>
              <option value="48">48小时</option>
              <option value="72">72小时</option>
              <option value="168">7天</option>
            </select>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowPredictionModal(false)}>
              取消
            </Button>
            <Button onClick={handleTimeSeriesPrediction} disabled={predictTimeSeriesMutation.isPending}>
              {predictTimeSeriesMutation.isPending ? '预测中...' : '预测'}
            </Button>
          </div>
        </div>
      </EnhancedModal>

      {/* Natural Language Modal */}
      <EnhancedModal
        open={showConversationModal}
        onOpenChange={setShowConversationModal}
        title="自然语言交互"
        size="md"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">用户输入</label>
            <textarea
              value={conversationData.user_input}
              onChange={(e) => setConversationData({ ...conversationData, user_input: e.target.value })}
              placeholder="输入你的问题或指令..."
              className="w-full px-3 py-2 border rounded-md bg-white min-h-[150px]"
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowConversationModal(false)}>
              取消
            </Button>
            <Button onClick={handleNaturalLanguage} disabled={naturalLanguageMutation.isPending}>
              {naturalLanguageMutation.isPending ? '处理中...' : '发送'}
            </Button>
          </div>
        </div>
      </EnhancedModal>
    </div>
  );
}