'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: 'GraphQL 订阅状态', path: '/api/graphql/graphql-subscription' },
];

export default function GraphqlSubscriptionPage() {
  return (
    <EndpointPanel
      title="GraphQL 订阅"
      intro="GraphQL 实时订阅（WebSocket）连接状态（/api/graphql/graphql-subscription）。"
      endpoints={ENDPOINTS}
    />
  );
}
