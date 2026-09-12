'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: 'Schema 概览', path: '/api/graphql/graphql-schema' },
  { label: 'Resolvers 概览', path: '/api/graphql/graphql-resolvers' },
  { label: '查询统计', path: '/api/graphql/graphql-query' },
];

export default function GraphqlApiPage() {
  return (
    <EndpointPanel
      title="GraphQL API"
      intro="GraphQL API 总体信息：schema、resolvers 与查询统计。"
      endpoints={ENDPOINTS}
    />
  );
}
