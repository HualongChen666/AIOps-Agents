'use client'

import { EndpointPanel } from '@/components/common/EndpointPanel';

const ENDPOINTS = [
  { label: 'GraphQL 查询信息', path: '/api/graphql/graphql-query' },
];

export default function GraphqlQueryPage() {
  return (
    <EndpointPanel
      title="GraphQL 查询"
      intro="查询配置、执行历史与性能统计（/api/graphql/graphql-query）。"
      endpoints={ENDPOINTS}
    />
  );
}
