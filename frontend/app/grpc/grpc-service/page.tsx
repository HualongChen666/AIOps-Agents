'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: 'gRPC 服务列表', path: '/api/grpc-services/list' },
  { label: 'gRPC 运行时状态', path: '/api/grpc-services/status' },
];

export default function GrpcServicePage() {
  return (
    <EndpointPanel
      title="gRPC 服务"
      intro="已注册的 gRPC 服务定义（/api/grpc-services/list）。"
      endpoints={ENDPOINTS}
    />
  );
}
