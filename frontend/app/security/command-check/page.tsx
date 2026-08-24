'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import api from '@/lib/api';

interface CheckResult {
  id: string;
  command: string;
  riskLevel: 'critical' | 'high' | 'medium' | 'low' | 'safe';
  riskScore: number;
  issues: string[];
  suggestions: string[];
  timestamp: string;
}

interface CheckHistory {
  id: string;
  command: string;
  riskLevel: string;
  timestamp: string;
  userId: string;
}

export default function CommandCheckPage() {
  const { isLoading, error, setLoading, setError } = useLoadingState(false);
  const { success, error: showError } = useToast();
  const [commandInput, setCommandInput] = useState('');
  const [checkResult, setCheckResult] = useState<CheckResult | null>(null);
  const [history, setHistory] = useState<CheckHistory[]>([]);
  const [stats, setStats] = useState({
    totalChecks: 0,
    criticalRisks: 0,
    highRisks: 0,
    safeCommands: 0,
  });

  const loadHistory = async () => {
    try {
      const [historyRes, statsRes] = await Promise.all([
        api.get('/api/v1/security/command-check/history'),
        api.get('/api/v1/security/command-check/stats'),
      ]);

      setHistory(historyRes.data?.history || []);
      setStats(statsRes.data || {
        totalChecks: 0,
        criticalRisks: 0,
        highRisks: 0,
        safeCommands: 0,
      });
    } catch (err) {
      console.error('Failed to load history:', err);
    }
  };

  const handleCheckCommand = async () => {
    if (!commandInput.trim()) {
      showError('请输入要检查的命令');
      return;
    }

    setLoading(true);
    try {
      const response = await api.post('/api/v1/security/command-check/check', {
        command: commandInput,
      });

      setCheckResult(response.data);
      success('命令检查完成');
      loadHistory();
      setLoading(false);
    } catch (err) {
      setError(err as Error);
      setLoading(false);
    }
  };

  const handleClearResult = () => {
    setCheckResult(null);
    setCommandInput('');
  };

  useEffect(() => {
    loadHistory();
  }, []);

  if (isLoading && !checkResult) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-600 dark:text-gray-400">Loading...</div>
      </div>
    );
  }

  if (error && !checkResult) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-red-600 dark:text-red-400">Error: {error.message}</div>
      </div>
    );
  }

  const getRiskColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'critical':
        return 'bg-red-100 text-red-800';
      case 'high':
        return 'bg-orange-100 text-orange-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-blue-100 text-blue-800';
      case 'safe':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getRiskTextColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'critical':
        return 'text-red-600';
      case 'high':
        return 'text-orange-600';
      case 'medium':
        return 'text-yellow-600';
      case 'low':
        return 'text-blue-600';
      case 'safe':
        return 'text-green-600';
      default:
        return 'text-gray-600';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">命令检查</h1>
        <Button onClick={loadHistory}>刷新数据</Button>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总检查次数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">{stats.totalChecks}</p>
            <p className="text-sm text-gray-500">命令检查</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">严重风险</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-600">{stats.criticalRisks}</p>
            <p className="text-sm text-gray-500">需要立即处理</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">高风险</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-orange-600">{stats.highRisks}</p>
            <p className="text-sm text-gray-500">需要关注</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">安全命令</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">{stats.safeCommands}</p>
            <p className="text-sm text-gray-500">通过检查</p>
          </CardContent>
        </Card>
      </div>

      {/* 命令检查输入 */}
      <Card>
        <CardHeader>
          <CardTitle>命令安全检查</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex gap-2">
              <Input
                value={commandInput}
                onChange={(e) => setCommandInput(e.target.value)}
                placeholder="输入要检查的命令，例如: rm -rf /var/log/*"
                className="flex-1 font-mono"
                onKeyPress={(e) => e.key === 'Enter' && handleCheckCommand()}
              />
              <Button onClick={handleCheckCommand} disabled={isLoading}>
                检查
              </Button>
              <Button variant="outline" onClick={handleClearResult}>
                清除
              </Button>
            </div>

            {/* 检查结果 */}
            {checkResult && (
              <div className="mt-4 space-y-4">
                <div className="p-4 border rounded-lg">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-semibold">检查结果</h3>
                    <Badge className={getRiskColor(checkResult.riskLevel)}>
                      {checkResult.riskLevel.toUpperCase()}
                    </Badge>
                  </div>
                  <div className="font-mono text-sm bg-gray-100 dark:bg-gray-800 p-3 rounded mb-3">
                    {checkResult.command}
                  </div>
                  <div className="mb-3">
                    <span className="text-sm text-gray-500">风险评分: </span>
                    <span className={`font-bold ${getRiskTextColor(checkResult.riskLevel)}`}>
                      {checkResult.riskScore}/100
                    </span>
                  </div>
                  <div className="mb-3">
                    <span className="text-sm text-gray-500">检查时间: </span>
                    <span className="text-sm">{new Date(checkResult.timestamp).toLocaleString()}</span>
                  </div>
                </div>

                {/* 问题列表 */}
                {checkResult.issues.length > 0 && (
                  <div className="p-4 border border-red-200 bg-red-50 dark:bg-red-900/20 rounded-lg">
                    <h4 className="font-semibold text-red-800 dark:text-red-200 mb-2">发现的问题</h4>
                    <ul className="list-disc list-inside space-y-1">
                      {checkResult.issues.map((issue, idx) => (
                        <li key={idx} className="text-sm text-red-700 dark:text-red-300">{issue}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* 建议列表 */}
                {checkResult.suggestions.length > 0 && (
                  <div className="p-4 border border-blue-200 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                    <h4 className="font-semibold text-blue-800 dark:text-blue-200 mb-2">安全建议</h4>
                    <ul className="list-disc list-inside space-y-1">
                      {checkResult.suggestions.map((suggestion, idx) => (
                        <li key={idx} className="text-sm text-blue-700 dark:text-blue-300">{suggestion}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 检查历史 */}
      <Card>
        <CardHeader>
          <CardTitle>检查历史</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>时间</TableHead>
                <TableHead>命令</TableHead>
                <TableHead>风险等级</TableHead>
                <TableHead>用户</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {history.length > 0 ? history.map((item) => (
                <TableRow key={item.id}>
                  <TableCell>{new Date(item.timestamp).toLocaleString()}</TableCell>
                  <TableCell className="font-mono text-sm">{item.command}</TableCell>
                  <TableCell>
                    <Badge className={getRiskColor(item.riskLevel)}>{item.riskLevel}</Badge>
                  </TableCell>
                  <TableCell>{item.userId}</TableCell>
                </TableRow>
              )) : (
                <TableRow>
                  <TableCell colSpan={4} className="text-center text-gray-500">
                    No check history found
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
