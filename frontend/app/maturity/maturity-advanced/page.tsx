'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface MaturityAssessment {
  id: string;
  assessment_name: string;
  status: string;
  overall_score: number;
  level: number;
  level_name: string;
  dimensions: any[];
  recommendations: any[];
  assessed_at: string;
  assessed_by: string;
  notes: string | null;
}

export default function MaturityAdvancedPage() {
  const [assessments, setAssessments] = useState<MaturityAssessment[]>([]);
  const [selectedAssessment, setSelectedAssessment] = useState<MaturityAssessment | null>(null);
  const [loading, setLoading] = useState(true);
  const [assessing, setAssessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newAssessment, setNewAssessment] = useState({
    assessment_name: '',
    notes: ''
  });

  useEffect(() => {
    fetchAssessments();
  }, []);

  const fetchAssessments = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.get('/api/v1/maturity/assessments');
      setAssessments(response.data.data || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载评估记录失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAssessment = async () => {
    try {
      setAssessing(true);
      setError(null);
      const response = await api.post('/api/v1/maturity/assessments', newAssessment);
      setShowCreateForm(false);
      setNewAssessment({
        assessment_name: '',
        notes: ''
      });
      await fetchAssessments();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '创建评估失败');
    } finally {
      setAssessing(false);
    }
  };

  const handleViewAssessment = async (assessmentId: string) => {
    try {
      setError(null);
      const response = await api.get(`/api/v1/maturity/assessments/${assessmentId}`);
      setSelectedAssessment(response.data.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '获取评估详情失败');
    }
  };

  const handleDeleteAssessment = async (assessmentId: string) => {
    if (!confirm('确定要删除此评估记录吗？')) return;

    try {
      setError(null);
      await api.delete(`/api/v1/maturity/assessments/${assessmentId}`);
      if (selectedAssessment?.id === assessmentId) {
        setSelectedAssessment(null);
      }
      await fetchAssessments();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '删除评估失败');
    }
  };

  const handleExportAssessment = async (assessmentId: string, format: string) => {
    try {
      setError(null);
      const response = await api.get(`/api/v1/maturity/assessments/${assessmentId}/export?format=${format}`);
      const data = response.data.data;
      
      if (format === 'json') {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `assessment-${assessmentId}.json`;
        a.click();
        URL.revokeObjectURL(url);
      } else {
        alert(JSON.stringify(data, null, 2));
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '导出评估失败');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed': return 'default';
      case 'in_progress': return 'secondary';
      case 'failed': return 'destructive';
      default: return 'outline';
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
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
        <h1 className="text-3xl font-bold text-gray-900">高级成熟度评估</h1>
        <Button onClick={fetchAssessments}>刷新</Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="text-red-800">{error}</div>
          <Button onClick={() => setError(null)} className="mt-2" variant="outline">关闭</Button>
        </div>
      )}

      {/* 创建评估表单 */}
      {showCreateForm && (
        <Card>
          <CardHeader>
            <CardTitle>创建新评估</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">评估名称</label>
                <input
                  type="text"
                  value={newAssessment.assessment_name}
                  onChange={(e) => setNewAssessment({ ...newAssessment, assessment_name: e.target.value })}
                  className="w-full border rounded-md p-2"
                  placeholder="输入评估名称"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">备注</label>
                <textarea
                  value={newAssessment.notes}
                  onChange={(e) => setNewAssessment({ ...newAssessment, notes: e.target.value })}
                  className="w-full border rounded-md p-2 h-24"
                  placeholder="评估备注（可选）"
                />
              </div>
              <div className="flex gap-2">
                <Button onClick={handleCreateAssessment} disabled={assessing} className="flex-1">
                  {assessing ? '评估中...' : '开始评估'}
                </Button>
                <Button onClick={() => setShowCreateForm(false)} variant="outline">取消</Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 评估列表 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>评估记录 ({assessments.length})</CardTitle>
            <Button onClick={() => setShowCreateForm(!showCreateForm)}>
              {showCreateForm ? '取消' : '创建评估'}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {assessments.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无评估记录</div>
          ) : (
            <div className="space-y-3">
              {assessments.map((assessment) => (
                <div key={assessment.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold">{assessment.assessment_name}</h3>
                    <div className="flex gap-2">
                      <Badge variant={getStatusColor(assessment.status)}>{assessment.status}</Badge>
                      <Badge variant="outline">等级 {assessment.level}</Badge>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm text-gray-600 mb-2">
                    <div>
                      <span className="text-gray-500">评分: </span>
                      <span className={`font-semibold ${getScoreColor(assessment.overall_score)}`}>
                        {assessment.overall_score}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500">等级名称: </span>
                      {assessment.level_name}
                    </div>
                    <div>
                      <span className="text-gray-500">评估人: </span>
                      {assessment.assessed_by}
                    </div>
                    <div>
                      <span className="text-gray-500">评估时间: </span>
                      {new Date(assessment.assessed_at).toLocaleString()}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleViewAssessment(assessment.id)}
                    >
                      查看详情
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleExportAssessment(assessment.id, 'json')}
                    >
                      导出JSON
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleExportAssessment(assessment.id, 'summary')}
                    >
                      导出摘要
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => handleDeleteAssessment(assessment.id)}
                    >
                      删除
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* 评估详情 */}
      {selectedAssessment && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>评估详情: {selectedAssessment.assessment_name}</CardTitle>
              <Button onClick={() => setSelectedAssessment(null)} variant="outline">关闭</Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {/* 基本信息 */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <div className="text-sm text-gray-500">状态</div>
                  <Badge variant={getStatusColor(selectedAssessment.status)}>{selectedAssessment.status}</Badge>
                </div>
                <div>
                  <div className="text-sm text-gray-500">总分</div>
                  <div className={`text-2xl font-semibold ${getScoreColor(selectedAssessment.overall_score)}`}>
                    {selectedAssessment.overall_score}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">等级</div>
                  <div className="text-2xl font-semibold">{selectedAssessment.level} - {selectedAssessment.level_name}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">评估人</div>
                  <div className="text-lg">{selectedAssessment.assessed_by}</div>
                </div>
              </div>

              {/* 维度详情 */}
              {selectedAssessment.dimensions && selectedAssessment.dimensions.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-3">维度详情</h3>
                  <div className="space-y-2">
                    {selectedAssessment.dimensions.map((dimension: any, index: number) => (
                      <div key={index} className="border rounded-lg p-3">
                        <div className="flex items-center justify-between mb-2">
                          <div className="font-semibold">{dimension.name || `维度 ${index + 1}`}</div>
                          <Badge variant="outline">{dimension.score || 0}分</Badge>
                        </div>
                        {dimension.description && (
                          <div className="text-sm text-gray-600">{dimension.description}</div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 改进建议 */}
              {selectedAssessment.recommendations && selectedAssessment.recommendations.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-3">改进建议 ({selectedAssessment.recommendations.length})</h3>
                  <div className="space-y-2">
                    {selectedAssessment.recommendations.map((rec: any, index: number) => (
                      <div key={index} className="border rounded-lg p-3">
                        <div className="font-semibold mb-1">{rec.title || `建议 ${index + 1}`}</div>
                        <div className="text-sm text-gray-600">{rec.description || rec}</div>
                        {rec.priority && (
                          <Badge variant="outline" className="mt-2">优先级: {rec.priority}</Badge>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 备注 */}
              {selectedAssessment.notes && (
                <div>
                  <h3 className="text-lg font-semibold mb-3">备注</h3>
                  <div className="text-sm text-gray-600 bg-gray-50 rounded-lg p-3">
                    {selectedAssessment.notes}
                  </div>
                </div>
              )}

              {/* 评估时间 */}
              <div className="text-xs text-gray-500">
                评估时间: {new Date(selectedAssessment.assessed_at).toLocaleString()}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
