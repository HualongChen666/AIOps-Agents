'use client'

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  Brain, 
  CheckCircle, 
  AlertTriangle, 
  TrendingUp, 
  Target,
  Lightbulb,
  FileText,
  Activity,
  Zap
} from 'lucide-react';

interface RootCauseHypothesis {
  hypothesis_id: string;
  root_cause: string;
  confidence: number;
  evidence: string[];
  causal_path: string[];
  impact_score: number;
  verification_status: string;
  verification_timestamp: string | null;
  recommended_action: string;
  requires_approval: boolean;
  expected_observations: string[];
  missing_data: string[];
  predicted_impact: Record<string, number>;
  is_multi_root?: boolean;
}

interface AIAnalysisResultProps {
  hypothesis: RootCauseHypothesis;
  onVerify?: (hypothesisId: string) => void;
  onApprove?: (hypothesisId: string) => void;
  onReject?: (hypothesisId: string) => void;
  showFullDetails?: boolean;
}

export const RootCauseAIAnalysis: React.FC<AIAnalysisResultProps> = ({
  hypothesis,
  onVerify,
  onApprove,
  onReject,
  showFullDetails = true,
}) => {
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'bg-green-500';
    if (confidence >= 0.6) return 'bg-blue-500';
    if (confidence >= 0.4) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getConfidenceLabel = (confidence: number) => {
    if (confidence >= 0.8) return '高置信度';
    if (confidence >= 0.6) return '中等置信度';
    if (confidence >= 0.4) return '低置信度';
    return '极低置信度';
  };

  const getVerificationStatusColor = (status: string) => {
    switch (status) {
      case 'verified':
        return 'bg-green-500';
      case 'partially_verified':
        return 'bg-yellow-500';
      case 'rejected':
        return 'bg-red-500';
      case 'in_progress':
        return 'bg-blue-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getVerificationStatusText = (status: string) => {
    switch (status) {
      case 'verified':
        return '已验证';
      case 'partially_verified':
        return '部分验证';
      case 'rejected':
        return '已拒绝';
      case 'in_progress':
        return '验证中';
      default:
        return '待验证';
    }
  };

  const getActionIcon = (action: string) => {
    switch (action) {
      case 'auto_heal':
        return <Zap className="h-4 w-4" />;
      case 'escalate':
        return <AlertTriangle className="h-4 w-4" />;
      case 'collect_more_data':
        return <Activity className="h-4 w-4" />;
      default:
        return <Lightbulb className="h-4 w-4" />;
    }
  };

  const getActionLabel = (action: string) => {
    switch (action) {
      case 'auto_heal':
        return '自动修复';
      case 'escalate':
        return '升级处理';
      case 'collect_more_data':
        return '收集更多数据';
      default:
        return action;
    }
  };

  return (
    <div className="space-y-4">
      {/* 主要结果卡片 */}
      <Card className="border-2 border-blue-200">
        <CardHeader className="bg-gradient-to-r from-blue-50 to-purple-50">
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-blue-600" />
            AI 根因分析结果
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 pt-4">
          {/* 根因和置信度 */}
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="text-sm text-gray-600 mb-1">识别的根因</div>
              <div className="text-lg font-semibold text-gray-900">
                {hypothesis.root_cause}
              </div>
              {hypothesis.is_multi_root && (
                <Badge variant="outline" className="mt-2">
                  <AlertTriangle className="h-3 w-3 mr-1" />
                  多根因场景
                </Badge>
              )}
            </div>
            <div className="text-right">
              <div className="text-sm text-gray-600 mb-1">AI 置信度</div>
              <div className="flex items-center gap-2">
                <Badge className={getConfidenceColor(hypothesis.confidence)}>
                  {(hypothesis.confidence * 100).toFixed(1)}%
                </Badge>
                <span className="text-xs text-gray-500">
                  {getConfidenceLabel(hypothesis.confidence)}
                </span>
              </div>
            </div>
          </div>

          {/* 推荐操作 */}
          <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
            <div className="flex items-center gap-2 mb-2">
              <Lightbulb className="h-4 w-4 text-blue-600" />
              <span className="font-medium text-blue-900">推荐操作</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {getActionIcon(hypothesis.recommended_action)}
                <span className="text-sm font-medium">
                  {getActionLabel(hypothesis.recommended_action)}
                </span>
              </div>
              {hypothesis.requires_approval && (
                <Badge variant="destructive" className="text-xs">
                  需要人工审批
                </Badge>
              )}
            </div>
          </div>

          {/* 影响评分 */}
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <div className="text-sm text-gray-600 mb-1">影响评分</div>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-orange-500 h-2 rounded-full transition-all"
                    style={{ width: `${hypothesis.impact_score * 100}%` }}
                  />
                </div>
                <span className="text-sm font-medium">
                  {hypothesis.impact_score.toFixed(2)}
                </span>
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-1">验证状态</div>
              <Badge className={getVerificationStatusColor(hypothesis.verification_status)}>
                {getVerificationStatusText(hypothesis.verification_status)}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {showFullDetails && (
        <>
          {/* 因果路径 */}
          {hypothesis.causal_path.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Target className="h-4 w-4" />
                  因果路径
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap items-center gap-2">
                  {hypothesis.causal_path.map((node, idx) => (
                    <React.Fragment key={idx}>
                      <Badge variant="outline" className="px-3 py-1">
                        {node}
                      </Badge>
                      {idx < hypothesis.causal_path.length - 1 && (
                        <span className="text-gray-400">→</span>
                      )}
                    </React.Fragment>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* 证据链 */}
          {hypothesis.evidence.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <FileText className="h-4 w-4" />
                  证据链
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {hypothesis.evidence.map((evidence, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm">
                      <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                      <span className="text-gray-700">{evidence}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {/* 预期观察 */}
          {hypothesis.expected_observations.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Activity className="h-4 w-4" />
                  预期观察
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {hypothesis.expected_observations.map((observation, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm">
                      <div className="w-2 h-2 bg-blue-500 rounded-full mt-1.5 flex-shrink-0" />
                      <span className="text-gray-700">{observation}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {/* 缺失数据 */}
          {hypothesis.missing_data.length > 0 && (
            <Card className="border-yellow-200">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base text-yellow-700">
                  <AlertTriangle className="h-4 w-4" />
                  缺失数据
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {hypothesis.missing_data.map((data, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm">
                      <div className="w-2 h-2 bg-yellow-500 rounded-full mt-1.5 flex-shrink-0" />
                      <span className="text-gray-700">{data}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {/* 预测影响 */}
          {Object.keys(hypothesis.predicted_impact).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <TrendingUp className="h-4 w-4" />
                  预测影响
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4">
                  {Object.entries(hypothesis.predicted_impact).map(([key, value]) => (
                    <div key={key} className="p-3 bg-gray-50 rounded-lg">
                      <div className="text-xs text-gray-600 mb-1">{key}</div>
                      <div className="text-lg font-semibold">
                        {(value * 100).toFixed(1)}%
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* 操作按钮 */}
          <div className="flex gap-2">
            {onVerify && (
              <Button
                onClick={() => onVerify(hypothesis.hypothesis_id)}
                disabled={hypothesis.verification_status === 'verified'}
                className="flex-1"
              >
                <CheckCircle className="h-4 w-4 mr-2" />
                验证假设
              </Button>
            )}
            {onApprove && hypothesis.requires_approval && (
              <Button
                onClick={() => onApprove(hypothesis.hypothesis_id)}
                variant="default"
                className="flex-1"
              >
                <CheckCircle className="h-4 w-4 mr-2" />
                批准执行
              </Button>
            )}
            {onReject && (
              <Button
                onClick={() => onReject(hypothesis.hypothesis_id)}
                variant="destructive"
                className="flex-1"
              >
                <AlertTriangle className="h-4 w-4 mr-2" />
                拒绝假设
              </Button>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default RootCauseAIAnalysis;
