'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { AlertTriangle, CheckCircle, XCircle, Clock } from 'lucide-react';

interface AlertItemProps {
  id: string;
  title: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  status: 'open' | 'acknowledged' | 'resolved';
  timestamp: string;
  service?: string;
  details?: string;
  onAcknowledge?: (id: string) => void;
  onResolve?: (id: string) => void;
  onView?: (id: string) => void;
}

export function AlertItem({
  id,
  title,
  severity,
  status,
  timestamp,
  service,
  details,
  onAcknowledge,
  onResolve,
  onView,
}: AlertItemProps) {
  const getSeverityColor = () => {
    switch (severity) {
      case 'critical':
        return 'bg-red-100 text-red-800';
      case 'high':
        return 'bg-orange-100 text-orange-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'open':
        return <AlertTriangle className="h-4 w-4 text-red-500" />;
      case 'acknowledged':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      case 'resolved':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      default:
        return <XCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  const getSeverityText = () => {
    switch (severity) {
      case 'critical':
        return '严重';
      case 'high':
        return '高';
      case 'medium':
        return '中';
      case 'low':
        return '低';
      default:
        return severity;
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'open':
        return '未处理';
      case 'acknowledged':
        return '已确认';
      case 'resolved':
        return '已解决';
      default:
        return status;
    }
  };

  return (
    <div className="flex items-start gap-4 p-4 border rounded-lg hover:bg-gray-50 transition">
      <div className="flex-shrink-0 mt-1">{getStatusIcon()}</div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <h4 className="font-medium text-gray-900 truncate">{title}</h4>
          <Badge className={getSeverityColor()} variant="outline">
            {getSeverityText()}
          </Badge>
        </div>
        {service && <p className="text-sm text-gray-500">{service}</p>}
        {details && <p className="text-sm text-gray-600 mt-1 line-clamp-2">{details}</p>}
        <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
          <span>{new Date(timestamp).toLocaleString()}</span>
          <span>•</span>
          <span>{getStatusText()}</span>
        </div>
      </div>
      <div className="flex flex-col gap-2">
        {onView && (
          <Button size="sm" variant="ghost" onClick={() => onView(id)}>
            查看
          </Button>
        )}
        {onAcknowledge && status === 'open' && (
          <Button size="sm" variant="outline" onClick={() => onAcknowledge(id)}>
            确认
          </Button>
        )}
        {onResolve && status !== 'resolved' && (
          <Button size="sm" onClick={() => onResolve(id)}>
            解决
          </Button>
        )}
      </div>
    </div>
  );
}