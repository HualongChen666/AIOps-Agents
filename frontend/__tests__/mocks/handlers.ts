import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';

// Mock data for alerts
const mockAlerts = [
  {
    id: 'alert-1',
    title: 'CPU使用率过高',
    severity: 'critical',
    status: 'open',
    timestamp: '2024-01-15T10:30:00Z',
    service: 'web-server',
    details: 'CPU使用率超过90%',
  },
  {
    id: 'alert-2',
    title: '内存不足',
    severity: 'high',
    status: 'acknowledged',
    timestamp: '2024-01-15T11:00:00Z',
    service: 'database',
    details: '内存使用率超过80%',
  },
  {
    id: 'alert-3',
    title: '磁盘空间不足',
    severity: 'medium',
    status: 'resolved',
    timestamp: '2024-01-15T12:00:00Z',
    service: 'storage',
    details: '磁盘使用率超过70%',
  },
];

// Mock data for authentication
const mockUser = {
  id: 1,
  username: 'admin',
  email: 'admin@example.com',
  role: 'admin',
};

const mockAuthResponse = {
  access_token: 'mock-jwt-token-12345',
  token_type: 'bearer',
  user: mockUser,
};

// Mock data for intelligence stats
const mockIntelligenceStats = {
  total_patterns: 150,
  noise_patterns: 25,
  cluster_count: 12,
  last_updated: new Date().toISOString(),
};

// Mock data for alert patterns
const mockAlertPatterns = {
  patterns: [
    {
      pattern_id: 'pattern-1',
      signature: 'cpu-high',
      frequency: 45,
      last_seen: new Date().toISOString(),
      is_noise: false,
    },
    {
      pattern_id: 'pattern-2',
      signature: 'memory-leak',
      frequency: 30,
      last_seen: new Date().toISOString(),
      is_noise: true,
      noise_reason: 'Known benign pattern',
    },
  ],
  total: 2,
};

// Mock data for anomaly records
const mockAnomalyRecords = [
  {
    id: 'anomaly-1',
    timestamp: '2024-01-15T10:00:00Z',
    metric: 'cpu_usage',
    actualValue: 95,
    predictedValue: 70,
    deviation: 35.7,
    confidence: 95,
  },
  {
    id: 'anomaly-2',
    timestamp: '2024-01-15T11:00:00Z',
    metric: 'memory_usage',
    actualValue: 85,
    predictedValue: 60,
    deviation: 41.7,
    confidence: 90,
  },
];

// Mock data for dashboard summary
const mockDashboardSummary = {
  total_alerts: 15,
  heal_rate: 85,
  mttd_min: 12,
  availability: 99.9,
};

// Mock data for metrics history
const mockMetricsHistory = {
  data: [
    {
      timestamp: '2024-01-15T00:00:00Z',
      cpu: 45,
      memory: 60,
      disk: 55,
    },
    {
      timestamp: '2024-01-15T01:00:00Z',
      cpu: 50,
      memory: 62,
      disk: 56,
    },
    {
      timestamp: '2024-01-15T02:00:00Z',
      cpu: 55,
      memory: 65,
      disk: 57,
    },
  ],
};

// Mock data for repair history
const mockRepairHistory = {
  records: [
    {
      id: 'repair-1',
      timestamp: '2024-01-15T10:00:00Z',
      type: 'auto',
      status: 'success',
      alert_id: 'alert-1',
      description: 'Auto-restarted web service',
    },
    {
      id: 'repair-2',
      timestamp: '2024-01-15T11:00:00Z',
      type: 'manual',
      status: 'success',
      alert_id: 'alert-2',
      description: 'Manually cleared cache',
    },
  ],
};

// Mock data for system health
const mockSystemHealth = {
  prometheus: { status: 'healthy', metrics_count: 1234 },
  grafana: { status: 'healthy', dashboards: 45 },
  zabbix: { status: 'healthy', triggers: 67 },
  cloudwatch: { status: 'healthy', alarms: 23 },
};

// Mock data for metrics
const mockMetrics = {
  metrics: [
    { key: 'Total Alerts', value: 15, unit: '', level: 'warning' },
    { key: 'Heal Success Rate', value: 85, unit: '%', level: 'normal' },
    { key: 'MTTD', value: 12, unit: 'min', level: 'normal' },
    { key: 'Availability', value: 99.9, unit: '%', level: 'normal' },
  ],
};

// Mock data for AI analysis
const mockAIAnalysis = {
  analysis: 'Based on the current metrics, the CPU usage spike is likely caused by increased traffic. Recommended action: Scale up the web server instances.',
  recommended_action: 'Scale up web server instances',
};

// Define handlers
export const handlers = [
  // Authentication API
  http.post('/api/v1/auth/login', async ({ request }) => {
    const body = await request.json() as { username: string; password: string };

    if (body.username === 'admin' && body.password === 'password') {
      return HttpResponse.json(mockAuthResponse);
    }

    return HttpResponse.json(
      { detail: 'Invalid credentials' },
      { status: 401 }
    );
  }),

  http.post('/api/v1/auth/logout', () => {
    return HttpResponse.json({ success: true });
  }),

  http.get('/api/v1/auth/me', () => {
    return HttpResponse.json(mockUser);
  }),

  http.post('/api/v1/auth/register-admin', () => {
    return HttpResponse.json(mockAuthResponse);
  }),

  // Alerts API
  http.get('/api/v1/alerts/', () => {
    return HttpResponse.json({ alerts: mockAlerts });
  }),

  http.post('/api/v1/alerts/:id/acknowledge', () => {
    return HttpResponse.json({ success: true });
  }),

  http.post('/api/v1/alerts/:id/resolve', () => {
    return HttpResponse.json({ success: true });
  }),

  http.delete('/api/v1/alerts/', () => {
    return HttpResponse.json({ success: true });
  }),

  // Intelligence API
  http.get('/api/v1/alerts/intelligence/statistics', () => {
    return HttpResponse.json(mockIntelligenceStats);
  }),

  http.get('/api/v1/alerts/intelligence/patterns', () => {
    return HttpResponse.json(mockAlertPatterns);
  }),

  // Anomaly API
  http.get('/api/v1/anomaly/records', () => {
    return HttpResponse.json(mockAnomalyRecords);
  }),

  http.get('/api/v1/anomaly/statistics', () => {
    return HttpResponse.json({
      cpu_usage: 10,
      memory_usage: 8,
      disk_usage: 5,
      total: 23,
    });
  }),

  // Dashboard API
  http.get('/api/v1/metrics/summary', () => {
    return HttpResponse.json(mockDashboardSummary);
  }),

  http.get('/api/v1/metrics/history', () => {
    return HttpResponse.json(mockMetricsHistory);
  }),

  http.get('/api/v1/repairs/history', () => {
    return HttpResponse.json(mockRepairHistory);
  }),

  http.get('/api/v1/health', () => {
    return HttpResponse.json(mockSystemHealth);
  }),

  // Metrics API
  http.get('/api/v1/metrics', () => {
    return HttpResponse.json(mockMetrics);
  }),

  // AI API
  http.post('/api/ai/analyze', () => {
    return HttpResponse.json(mockAIAnalysis);
  }),

  // Health ping
  http.get('/api/v1/health/ping', () => {
    return HttpResponse.json({ status: 'ok' });
  }),

  // Settings API
  http.get('/api/settings/', () => {
    return HttpResponse.json({
      settings: {
        system_name: 'AIOps Agent',
        timezone: 'Asia/Shanghai',
        language: 'zh-CN',
        data_retention: '30d',
      },
    });
  }),

  http.put('/api/settings/', async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({ settings: body });
  }),

  // Assets API
  http.get('/api/v1/assets/', () => {
    return HttpResponse.json([
      {
        id: 1,
        name: 'Web Server',
        service: 'nginx',
        business_unit: 'Platform',
        env: 'prod',
        owner: 'team-a',
        created_at: '2024-01-15T10:00:00Z',
      },
      {
        id: 2,
        name: 'Database',
        service: 'postgresql',
        business_unit: 'Platform',
        env: 'prod',
        owner: 'team-b',
        created_at: '2024-01-15T11:00:00Z',
      },
    ]);
  }),

  http.post('/api/v1/assets/', async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      id: 3,
      ...body,
      created_at: new Date().toISOString(),
    });
  }),

  http.put('/api/v1/assets/:id', async ({ request, params }) => {
    const body = await request.json();
    return HttpResponse.json({
      id: Number(params.id),
      ...body,
      created_at: '2024-01-15T10:00:00Z',
    });
  }),

  http.delete('/api/v1/assets/:id', () => {
    return HttpResponse.json({ success: true });
  }),
];

// Create server
export const server = setupServer(...handlers);
