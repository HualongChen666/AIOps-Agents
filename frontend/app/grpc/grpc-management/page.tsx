'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: 'gRPC 服务状态', path: '/api/grpc-services/status' },
  { label: 'gRPC 服务列表', path: '/api/grpc-services/list' },
];

export default function GrpcManagementPage() {
  return (
    <EndpointPanel
      title="gRPC 管理"
      intro="gRPC 服务的注册状态与清单（/api/grpc-services/*）。"
      endpoints={ENDPOINTS}
    />
  );
}
