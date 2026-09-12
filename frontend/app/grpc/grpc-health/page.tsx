'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: 'gRPC 健康检查', path: '/api/grpc/health' },
];

export default function GrpcHealthPage() {
  return (
    <EndpointPanel
      title="gRPC 健康检查"
      intro="来自 gRPC 服务端点的真实健康状态（/api/grpc/health）。"
      endpoints={ENDPOINTS}
    />
  );
}
