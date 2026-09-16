import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Pages below talk to the backend through the shared axios client.
jest.mock('@/lib/api');
const mockedApi = require('@/lib/api').default as jest.Mocked<{
  get: jest.Mock;
  post: jest.Mock;
  put: jest.Mock;
  patch: jest.Mock;
  delete: jest.Mock;
}>;

// Heavy presentational children of the overview page pull in react-query /
// websocket transports; stub them so the test isolates the refresh logic.
jest.mock('@/components/DashboardCards', () => ({ DashboardCards: () => null }));
jest.mock('@/components/AlertStream', () => ({ AlertStream: () => null }));
jest.mock('@/components/SystemHealth', () => ({ SystemHealth: () => null }));
jest.mock('@/components/MetricsChart', () => ({ MetricsChart: () => null }));
jest.mock('@/components/QuickActions', () => ({ QuickActions: () => null }));

import OverviewPage from '@/app/overview/page';
import SLOMonitoringPage from '@/app/slo/slo-monitoring/page';
import KPIConfigPage from '@/app/slo/kpi-config/page';
import AccessibilityPage from '@/app/accessibility/page';
import AIFeedbackPage from '@/app/ai/ai-feedback/page';
import CostOptimizerPage from '@/app/ai/cost-optimizer/page';
import AnomalyPage from '@/app/anomaly/page';
import ApiDocumentationPage from '@/app/api-documentation/page';

const renderPage = (ui: React.ReactElement) => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
};

beforeEach(() => {
  window.localStorage.clear();
  mockedApi.get.mockResolvedValue({ data: {} });
  mockedApi.post.mockResolvedValue({ data: {} });
  mockedApi.put.mockResolvedValue({ data: {} });
  mockedApi.patch.mockResolvedValue({ data: {} });
  mockedApi.delete.mockResolvedValue({ data: {} });
});

describe('medium-ledger batch14 — page defects fixed with real behaviour', () => {
  describe('FE-106 app/overview — refresh must not report success on a failed probe', () => {
    it('surfaces the HTTP failure instead of silently "succeeding"', async () => {
      (global as any).fetch = jest
        .fn()
        .mockResolvedValue({ ok: false, status: 503, json: async () => ({}) });

      renderPage(<OverviewPage />);

      await waitFor(() => expect(screen.getByText(/Error: HTTP 503/)).toBeInTheDocument());
    });

    it('renders the real backend status on success', async () => {
      (global as any).fetch = jest
        .fn()
        .mockResolvedValue({ ok: true, status: 200, json: async () => ({ status: 'alive' }) });

      renderPage(<OverviewPage />);

      const badge = await screen.findByTestId('backend-status');
      expect(badge).toHaveTextContent('后端: alive');
    });
  });

  describe('FE-130 app/slo/slo-monitoring — polling must not blank the list', () => {
    it('keeps the loaded monitors visible when refreshing', async () => {
      mockedApi.get.mockResolvedValue({
        data: {
          slos: [
            {
              id: 's1',
              name: 'API可用性',
              service: 'api',
              metric: 'availability',
              current: 99.9,
              target: 99.5,
              errorBudget: 50,
              burnRate: 1.2,
              window: '30d',
              status: 'healthy',
            },
          ],
        },
      });

      renderPage(<SLOMonitoringPage />);

      expect(await screen.findByText('API可用性')).toBeInTheDocument();

      fireEvent.click(screen.getByText('刷新'));

      expect(screen.queryByText('加载中...')).not.toBeInTheDocument();
      expect(screen.getByText('API可用性')).toBeInTheDocument();
    });
  });

  describe('FE-131 app/slo/kpi-config — one PUT per committed edit, not per keystroke', () => {
    it('does not call the API while typing and commits on blur', async () => {
      mockedApi.get.mockResolvedValue({
        data: {
          configs: [
            {
              id: 'k1',
              kpi_id: 'kpi-1',
              kpi_name: 'QPS',
              data_source: 'prometheus',
              query: 'rate(x)',
              aggregation: 'avg',
              interval: '1m',
              alert_threshold: 10,
              alert_enabled: true,
            },
          ],
        },
      });

      renderPage(<KPIConfigPage />);

      const input = await screen.findByDisplayValue('prometheus');
      fireEvent.change(input, { target: { value: 'prometheus-prod' } });

      // Typing alone must not hit the backend.
      expect(mockedApi.put).not.toHaveBeenCalled();

      fireEvent.blur(input);

      await waitFor(() =>
        expect(mockedApi.put).toHaveBeenCalledWith('/api/v1/slo/kpi-config/k1', {
          data_source: 'prometheus-prod',
        })
      );
      expect(mockedApi.put).toHaveBeenCalledTimes(1);
    });
  });

  describe('FE-141 app/accessibility — keyboard listeners are bound once', () => {
    it('does not re-subscribe window listeners on every keypress', () => {
      const addSpy = jest.spyOn(window, 'addEventListener');

      renderPage(<AccessibilityPage />);

      const keyCalls = () =>
        addSpy.mock.calls.filter((c) => c[0] === 'keydown' || c[0] === 'keyup').length;

      // one keydown + one keyup on mount
      expect(keyCalls()).toBe(2);

      fireEvent.keyDown(window, { key: 'a' });
      fireEvent.keyUp(window, { key: 'a' });

      // still only the original two subscriptions — no per-keypress rebind
      expect(keyCalls()).toBe(2);

      addSpy.mockRestore();
    });
  });

  describe('FE-144 app/ai/ai-feedback — missing avg_rating must not crash the page', () => {
    it('renders 0.0 when the backend omits avg_rating', async () => {
      mockedApi.get.mockImplementation((url: string) => {
        if (url.endsWith('/stats')) {
          return Promise.resolve({ data: { total: 1, positive: 1, negative: 0, suggestions: 0 } });
        }
        return Promise.resolve({ data: { feedbacks: [] } });
      });

      renderPage(<AIFeedbackPage />);

      expect(await screen.findByText('平均评分')).toBeInTheDocument();
      expect(screen.getByText('0.0')).toBeInTheDocument();
    });
  });

  describe('FE-146 app/ai/cost-optimizer — empty data renders finite numbers', () => {
    it('shows 0 / $0.0000 instead of NaN or Infinity', async () => {
      mockedApi.get.mockImplementation((url: string) => {
        if (url.includes('/costs')) {
          return Promise.resolve({
            data: { period: '7d', total_cost: 0, by_model: [], by_service: [] },
          });
        }
        return Promise.resolve({ data: { suggestions: [] } });
      });

      renderPage(<CostOptimizerPage />);

      expect(await screen.findByText('总成本')).toBeInTheDocument();
      expect(screen.getByText('$0.00')).toBeInTheDocument();
      expect(screen.getByText('$0.0000')).toBeInTheDocument();
      expect(screen.queryByText(/NaN/)).not.toBeInTheDocument();
      expect(screen.queryByText(/Infinity/)).not.toBeInTheDocument();
    });
  });

  describe('FE-204 app/anomaly — real chart, controlled config, live buttons', () => {
    const mockAnomalyData = () => {
      mockedApi.get.mockImplementation((url: string) => {
        if (url.endsWith('/records')) {
          return Promise.resolve({
            data: [
              { id: 'r-low', timestamp: '2026-09-01T00:00:00Z', metric: 'cpu', actualValue: 90, predictedValue: 60, deviation: 50, confidence: 90 },
              { id: 'r-high', timestamp: '2026-09-02T00:00:00Z', metric: 'memory', actualValue: 95, predictedValue: 60, deviation: 58, confidence: 99 },
            ],
          });
        }
        return Promise.resolve({ data: { cpu: 2, memory: 1, net_in: 0, total: 3 } });
      });
    };

    it('renders a real bar per metric from the statistics payload', async () => {
      mockAnomalyData();
      renderPage(<AnomalyPage />);

      await waitFor(() => expect(screen.getByTestId('anomaly-bar-cpu')).toBeInTheDocument());
      expect(screen.getByTestId('anomaly-bar-memory')).toBeInTheDocument();
      expect(screen.queryByText('时序图表区域')).not.toBeInTheDocument();
    });

    it('applies the confidence threshold to the visible records', async () => {
      mockAnomalyData();
      renderPage(<AnomalyPage />);

      // default applied threshold (95%) hides the 90%-confidence record
      expect(await screen.findByText('r-high')).toBeInTheDocument();
      expect(screen.queryByText('r-low')).not.toBeInTheDocument();

      fireEvent.change(screen.getByLabelText('置信度阈值 (%)'), { target: { value: '90' } });
      fireEvent.click(screen.getByText('应用配置'));

      expect(await screen.findByText('r-low')).toBeInTheDocument();
    });

    it('persists the model configuration on save', async () => {
      mockAnomalyData();
      renderPage(<AnomalyPage />);
      await screen.findByTestId('anomaly-bar-cpu');

      fireEvent.change(screen.getByLabelText('异常检测灵敏度'), { target: { value: 'high' } });
      fireEvent.click(screen.getByText('保存配置'));

      const saved = JSON.parse(window.localStorage.getItem('anomaly-model-config') || '{}');
      expect(saved.sensitivity).toBe('high');
      expect(await screen.findByTestId('config-saved')).toBeInTheDocument();
    });
  });

  describe('FE-208 app/api-documentation — endpoints come from the real OpenAPI spec', () => {
    it('derives version, format, auth scheme and operations from /openapi.json', async () => {
      const spec = {
        openapi: '3.1.0',
        info: { version: '9.9.9', title: 'AIOps' },
        paths: {
          '/api/v1/alerts': {
            get: { summary: '列出告警', tags: ['告警'] },
            post: { summary: '创建告警', tags: ['告警'] },
          },
        },
        components: { securitySchemes: { bearer: { type: 'http', scheme: 'bearer' } } },
      };
      (global as any).fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => spec });

      renderPage(<ApiDocumentationPage />);

      expect(await screen.findByText('9.9.9')).toBeInTheDocument();
      expect(screen.getByText('OpenAPI 3.1.0')).toBeInTheDocument();
      expect(screen.getByText('http bearer')).toBeInTheDocument();

      fireEvent.click(screen.getByRole('button', { name: /API端点/ }));
      expect(await screen.findByText('列出告警')).toBeInTheDocument();
      expect(screen.getByText('创建告警')).toBeInTheDocument();
    });
  });
});
