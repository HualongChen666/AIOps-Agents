'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: 'GraphQL Schema', path: '/api/graphql/graphql-schema' },
];

export default function GraphqlSchemaPage() {
  return (
    <EndpointPanel
      title="GraphQL Schema"
      intro="运行时 GraphQL schema（真实内省结果，/api/graphql/graphql-schema）。"
      endpoints={ENDPOINTS}
    />
  );
}
