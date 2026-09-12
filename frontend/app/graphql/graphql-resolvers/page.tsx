'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: 'GraphQL Resolvers', path: '/api/graphql/graphql-resolvers' },
];

export default function GraphqlResolversPage() {
  return (
    <EndpointPanel
      title="GraphQL Resolvers"
      intro="已注册的 resolver 与其调用统计（/api/graphql/graphql-resolvers）。"
      endpoints={ENDPOINTS}
    />
  );
}
