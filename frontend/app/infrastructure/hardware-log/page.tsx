'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface Vendor {
  value: string;
  name: string;
}

interface Component {
  value: string;
  name: string;
}

interface ComponentIssue {
  component: string;
  severity: string;
  issue_type: string;
  description: string;
  affected_units: string[];
  risk_level: string;
  repair_recommendations: string[];
  script_keys: string[];
  log_entry_count: number;
}

interface AnalysisResult {
  vendor: string;
  total_entries: number;
  issues: ComponentIssue[];
  summary: {
    vendor: string;
    total_entries: number;
    components_analyzed: number;
    issues_found: number;
    critical_issues: number;
    error_issues: number;
    warning_issues: number;
  };
  analysis_timestamp: string;
  repair_plan: {
    analysis_summary: any;
    total_issues: number;
    prioritized_actions: any[];
    estimated_downtime: number;
    requires_maintenance_window: boolean;
  };
  auto_repair_results?: any[];
}

export default function HardwareLogPage() {
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [components, setComponents] = useState<Component[]>([]);
  const [selectedVendor, setSelectedVendor] = useState<string>('');
  const [logContent, setLogContent] = useState<string>('');
  const [autoTriggerRepair, setAutoTriggerRepair] = useState<boolean>(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMetadata();
  }, []);

  const fetchMetadata = async () => {
    try {
      setLoading(true);
      setError(null);
      const [vendorsRes, componentsRes] = await Promise.all([
        api.get('/api/v1/hardware-logs/vendors'),
        api.get('/api/v1/hardware-logs/components')
      ]);
      setVendors(vendorsRes.data.vendors || []);
      setComponents(componentsRes.data.components || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载元数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeLog = async () => {
    if (!logContent.trim()) {
      setError('请输入日志内容');
      return;
    }

    try {
      setAnalyzing(true);
      setError(null);
      const response = await api.post('/api/v1/hardware-logs/analyze', {
        log_content: logContent,
        vendor: selectedVendor || null,
        auto_trigger_repair: autoTriggerRepair
      });
      setAnalysisResult(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '分析日志失败');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleTriggerRepair = async (issueIndex: number) => {
    if (!analysisResult) return;

    try {
      setError(null);
      const response = await api.post('/api/v1/hardware-logs/repair/trigger', {
        analysis_id: `analysis-${Date.now()}`,
        issue_index: issueIndex,
        script_key: analysisResult.issues[issueIndex]?.script_keys[0] || null,
        params: {},
        force: false
      });
      alert('修复触发成功');
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '触发修复失败');
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical': return 'destructive';
      case 'error': return 'destructive';
      case 'warning': return 'secondary';
      default: return 'default';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">硬件日志分析</h1>
        <Button onClick={fetchMetadata}>刷新</Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="text-red-800">{error}</div>
          <Button onClick={() => setError(null)} className="mt-2" variant="outline">关闭</Button>
        </div>
      )}

      {/* 日志输入 */}
      <Card>
        <CardHeader>
          <CardTitle>日志分析</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">硬件厂商</label>
              <select
                value={selectedVendor}
                onChange={(e) => setSelectedVendor(e.target.value)}
                className="w-full border rounded-md p-2"
              >
                <option value="">自动检测</option>
                {vendors.map((vendor) => (
                  <option key={vendor.value} value={vendor.value}>{vendor.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">日志内容</label>
              <textarea
                value={logContent}
                onChange={(e) => setLogContent(e.target.value)}
                className="w-full border rounded-md p-2 h-64 font-mono text-sm"
                placeholder="粘贴硬件日志内容..."
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="autoRepair"
                checked={autoTriggerRepair}
                onChange={(e) => setAutoTriggerRepair(e.target.checked)}
              />
              <label htmlFor="autoRepair" className="text-sm text-gray-700">
                自动触发关键问题修复
              </label>
            </div>
            <Button
              onClick={handleAnalyzeLog}
              disabled={analyzing}
              className="w-full"
            >
              {analyzing ? '分析中...' : '分析日志'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 分析结果 */}
      {analysisResult && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>分析摘要</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <div className="text-sm text-gray-500">厂商</div>
                  <div className="text-lg font-semibold">{analysisResult.vendor}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">日志条目</div>
                  <div className="text-lg font-semibold">{analysisResult.total_entries}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">发现问题</div>
                  <div className="text-lg font-semibold">{analysisResult.summary.issues_found}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">关键问题</div>
                  <div className="text-lg font-semibold text-red-600">{analysisResult.summary.critical_issues}</div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>检测到的问题 ({analysisResult.issues.length})</CardTitle>
            </CardHeader>
            <CardContent>
              {analysisResult.issues.length === 0 ? (
                <div className="text-gray-500 text-center py-8">未检测到问题</div>
              ) : (
                <div className="space-y-4">
                  {analysisResult.issues.map((issue, index) => (
                    <div key={index} className="border rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="font-semibold">{issue.component}</h3>
                        <Badge variant={getSeverityColor(issue.severity)}>
                          {issue.severity}
                        </Badge>
                      </div>
                      <div className="text-sm text-gray-600 mb-2">{issue.description}</div>
                      <div className="text-xs text-gray-500 mb-2">
                        类型: {issue.issue_type} | 风险等级: {issue.risk_level} | 日志条目: {issue.log_entry_count}
                      </div>
                      {issue.affected_units.length > 0 && (
                        <div className="text-xs text-gray-500 mb-2">
                          受影响单元: {issue.affected_units.join(', ')}
                        </div>
                      )}
                      {issue.repair_recommendations.length > 0 && (
                        <div className="mb-2">
                          <div className="text-sm font-medium text-gray-700 mb-1">修复建议:</div>
                          <ul className="text-sm text-gray-600 list-disc list-inside">
                            {issue.repair_recommendations.map((rec, i) => (
                              <li key={i}>{rec}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {issue.script_keys.length > 0 && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleTriggerRepair(index)}
                        >
                          触发修复
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {analysisResult.auto_repair_results && analysisResult.auto_repair_results.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>自动修复结果</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {analysisResult.auto_repair_results.map((result: any, index: number) => (
                    <div key={index} className="border rounded-lg p-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm">问题 #{result.issue_index}</span>
                        <Badge variant={result.success ? 'default' : 'destructive'}>
                          {result.success ? '成功' : '失败'}
                        </Badge>
                      </div>
                      {result.error && (
                        <div className="text-xs text-red-600 mt-1">{result.error}</div>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
