'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: 'GraphQL 认证', path: '/api/graphql/graphql-auth' },
];

export default function GraphqlAuthPage() {
  return (
    <EndpointPanel
      title="GraphQL 认证"
      intro="GraphQL 端点的鉴权配置与状态（/api/graphql/graphql-auth）。"
      endpoints={ENDPOINTS}
    />
  );
}
