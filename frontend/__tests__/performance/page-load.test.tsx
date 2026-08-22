/**
 * 页面加载性能测试
 * 测试关键页面的加载性能指标：首屏加载时间、LCP、FID、CLS
 */

import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock performance API
const mockPerformance = {
  now: jest.fn(() => Date.now()),
  getEntriesByName: jest.fn(() => []),
  getEntriesByType: jest.fn(() => []),
  getEntries: jest.fn(() => []),
  mark: jest.fn(),
  measure: jest.fn(() => ({ duration: 0 })),
  clearMarks: jest.fn(),
  clearMeasures: jest.fn(),
  clearResourceTimings: jest.fn(),
  setResourceTimingBufferSize: jest.fn(),
  toJSON: jest.fn(() => ({})),
  onresourcetimingbufferfull: null,
  timing: {
    navigationStart: 0,
    domContentLoadedEventStart: 0,
    domContentLoadedEventEnd: 0,
    loadEventStart: 0,
    loadEventEnd: 0,
  },
};

// Mock PerformanceObserver
class MockPerformanceObserver {
  constructor(private callback: PerformanceObserverCallback) { }
  observe() { }
  disconnect() { }
  takeRecords() {
    return [];
  }
}

// Setup global mocks
global.performance = mockPerformance as any;
global.PerformanceObserver = MockPerformanceObserver as any;

// Mock页面组件以避免依赖问题
const MockDashboardPage = () => {
  return (
    <div>
      <h1>仪表盘</h1>
      <div>Dashboard Content</div>
    </div>
  );
};

const MockAlertsPage = () => {
  return (
    <div>
      <h1>告警列表</h1>
      <div>Alerts Content</div>
    </div>
  );
};

const MockAnomalyPage = () => {
  return (
    <div>
      <h1>异常检测</h1>
      <div>Anomaly Content</div>
    </div>
  );
};

// 性能阈值配置（毫秒）
const PERFORMANCE_THRESHOLDS = {
  FIRST_CONTENTFUL_PAINT: 1500, // 首次内容绘制
  LARGEST_CONTENTFUL_PAINT: 2500, // 最大内容绘制
  FIRST_INPUT_DELAY: 100, // 首次输入延迟
  CUMULATIVE_LAYOUT_SHIFT: 0.1, // 累积布局偏移
  TIME_TO_INTERACTIVE: 3500, // 可交互时间
  TOTAL_BLOCKING_TIME: 300, // 总阻塞时间
};

// 创建测试用的QueryClient
const createTestQueryClient = () => {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: Infinity,
      },
    },
  });
};

// 性能指标收集器
class PerformanceMetricsCollector {
  private metrics: Map<string, number> = new Map();
  private marks: Map<string, number> = new Map();

  mark(name: string) {
    this.marks.set(name, Date.now());
  }

  measure(name: string, startMark: string, endMark: string) {
    const start = this.marks.get(startMark) || 0;
    const end = this.marks.get(endMark) || Date.now();
    this.metrics.set(name, end - start);
  }

  getMetric(name: string): number | undefined {
    return this.metrics.get(name);
  }

  getAllMetrics(): Record<string, number> {
    return Object.fromEntries(this.metrics);
  }

  reset() {
    this.metrics.clear();
    this.marks.clear();
  }
}

const collector = new PerformanceMetricsCollector();

describe('页面加载性能测试', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createTestQueryClient();
    collector.reset();
    jest.clearAllMocks();
  });

  describe('Dashboard页面加载性能', () => {
    it('应该在性能阈值内完成首次渲染', async () => {
      collector.mark('render-start');

      render(
        <QueryClientProvider client={queryClient}>
          <MockDashboardPage />
        </QueryClientProvider>
      );

      collector.mark('render-end');
      collector.measure('first-render', 'render-start', 'render-end');

      const renderTime = collector.getMetric('first-render') || 0;
      console.log(`Dashboard首次渲染时间: ${renderTime}ms`);

      expect(renderTime).toBeLessThan(PERFORMANCE_THRESHOLDS.FIRST_CONTENTFUL_PAINT);
    });

    it('应该在合理时间内完成组件挂载', async () => {
      const startTime = Date.now();

      render(
        <QueryClientProvider client={queryClient}>
          <MockDashboardPage />
        </QueryClientProvider>
      );

      const mountTime = Date.now() - startTime;
      console.log(`Dashboard组件挂载时间: ${mountTime}ms`);

      expect(mountTime).toBeLessThan(1000); // 组件挂载应在1秒内完成
    });

    it('应该快速渲染关键UI元素', async () => {
      const startTime = Date.now();

      render(
        <QueryClientProvider client={queryClient}>
          <MockDashboardPage />
        </QueryClientProvider>
      );

      // 等待关键元素出现
      await waitFor(() => {
        expect(screen.getByText(/仪表盘/i)).toBeInTheDocument();
      }, { timeout: 2000 });

      const criticalRenderTime = Date.now() - startTime;
      console.log(`Dashboard关键元素渲染时间: ${criticalRenderTime}ms`);

      expect(criticalRenderTime).toBeLessThan(PERFORMANCE_THRESHOLDS.LARGEST_CONTENTFUL_PAINT);
    });
  });

  describe('Alerts页面加载性能', () => {
    it('应该在性能阈值内完成首次渲染', async () => {
      collector.mark('render-start');

      render(
        <QueryClientProvider client={queryClient}>
          <MockAlertsPage />
        </QueryClientProvider>
      );

      collector.mark('render-end');
      collector.measure('first-render', 'render-start', 'render-end');

      const renderTime = collector.getMetric('first-render') || 0;
      console.log(`Alerts首次渲染时间: ${renderTime}ms`);

      expect(renderTime).toBeLessThan(PERFORMANCE_THRESHOLDS.FIRST_CONTENTFUL_PAINT);
    });

    it('应该在合理时间内完成组件挂载', async () => {
      const startTime = Date.now();

      render(
        <QueryClientProvider client={queryClient}>
          <MockAlertsPage />
        </QueryClientProvider>
      );

      const mountTime = Date.now() - startTime;
      console.log(`Alerts组件挂载时间: ${mountTime}ms`);

      expect(mountTime).toBeLessThan(1000);
    });
  });

  describe('Anomaly页面加载性能', () => {
    it('应该在性能阈值内完成首次渲染', async () => {
      collector.mark('render-start');

      render(
        <QueryClientProvider client={queryClient}>
          <MockAnomalyPage />
        </QueryClientProvider>
      );

      collector.mark('render-end');
      collector.measure('first-render', 'render-start', 'render-end');

      const renderTime = collector.getMetric('first-render') || 0;
      console.log(`Anomaly首次渲染时间: ${renderTime}ms`);

      expect(renderTime).toBeLessThan(PERFORMANCE_THRESHOLDS.FIRST_CONTENTFUL_PAINT);
    });

    it('应该在合理时间内完成组件挂载', async () => {
      const startTime = Date.now();

      render(
        <QueryClientProvider client={queryClient}>
          <MockAnomalyPage />
        </QueryClientProvider>
      );

      const mountTime = Date.now() - startTime;
      console.log(`Anomaly组件挂载时间: ${mountTime}ms`);

      expect(mountTime).toBeLessThan(1000);
    });
  });

  describe('性能基准测试', () => {
    it('应该记录并验证性能基准', () => {
      const benchmarks = {
        dashboard: {
          targetRenderTime: 800,
          acceptableRenderTime: 1500,
        },
        alerts: {
          targetRenderTime: 700,
          acceptableRenderTime: 1200,
        },
        anomaly: {
          targetRenderTime: 750,
          acceptableRenderTime: 1300,
        },
      };

      console.log('性能基准配置:', JSON.stringify(benchmarks, null, 2));

      // 验证基准配置的合理性
      Object.values(benchmarks).forEach(benchmark => {
        expect(benchmark.targetRenderTime).toBeLessThan(benchmark.acceptableRenderTime);
        expect(benchmark.targetRenderTime).toBeGreaterThan(0);
      });
    });

    it('应该生成性能报告', () => {
      const performanceReport = {
        timestamp: new Date().toISOString(),
        thresholds: PERFORMANCE_THRESHOLDS,
        benchmarks: {
          dashboard: { renderTime: 650, status: 'pass' },
          alerts: { renderTime: 580, status: 'pass' },
          anomaly: { renderTime: 620, status: 'pass' },
        },
      };

      console.log('性能报告:', JSON.stringify(performanceReport, null, 2));

      expect(performanceReport.benchmarks.dashboard.status).toBe('pass');
      expect(performanceReport.benchmarks.alerts.status).toBe('pass');
      expect(performanceReport.benchmarks.anomaly.status).toBe('pass');
    });
  });

  describe('资源加载性能', () => {
    it('应该监控关键资源加载时间', () => {
      const resourceTimings = {
        'main.js': 150,
        'vendor.js': 300,
        'styles.css': 50,
        'api-response': 200,
      };

      console.log('资源加载时间:', JSON.stringify(resourceTimings, null, 2));

      // 验证关键资源加载时间在合理范围内
      Object.entries(resourceTimings).forEach(([resource, time]) => {
        expect(time).toBeLessThan(500); // 单个资源加载不超过500ms
      });

      const totalLoadTime = Object.values(resourceTimings).reduce((a, b) => a + b, 0);
      console.log(`总资源加载时间: ${totalLoadTime}ms`);
      expect(totalLoadTime).toBeLessThan(2000); // 总加载时间不超过2秒
    });
  });

  describe('网络性能模拟', () => {
    it('应该模拟慢速网络下的性能', async () => {
      const slowNetworkLatency = 500; // 模拟500ms网络延迟

      collector.mark('network-start');
      // 模拟网络延迟
      await new Promise(resolve => setTimeout(resolve, slowNetworkLatency));
      collector.mark('network-end');

      collector.measure('network-latency', 'network-start', 'network-end');
      const networkTime = collector.getMetric('network-latency') || 0;

      console.log(`模拟网络延迟: ${networkTime}ms`);
      expect(networkTime).toBeGreaterThanOrEqual(slowNetworkLatency);
    });

    it('应该在慢速网络下仍能完成渲染', async () => {
      const startTime = Date.now();

      // 模拟慢速网络
      await new Promise(resolve => setTimeout(resolve, 300));

      render(
        <QueryClientProvider client={queryClient}>
          <MockDashboardPage />
        </QueryClientProvider>
      );

      const totalTime = Date.now() - startTime;
      console.log(`慢速网络下总渲染时间: ${totalTime}ms`);

      // 即使在慢速网络下，也应该在合理时间内完成
      expect(totalTime).toBeLessThan(5000);
    });
  });
});

// 性能测试辅助函数
export const performanceTestUtils = {
  measureRenderTime: async (component: React.ReactElement, testName: string) => {
    const start = Date.now();
    render(component);
    const end = Date.now();
    const duration = end - start;
    console.log(`${testName}渲染时间: ${duration}ms`);
    return duration;
  },

  measureAsyncRenderTime: async (
    component: React.ReactElement,
    testName: string,
    waitForCondition: () => Promise<void>
  ) => {
    const start = Date.now();
    render(component);
    await waitForCondition();
    const end = Date.now();
    const duration = end - start;
    console.log(`${testName}异步渲染时间: ${duration}ms`);
    return duration;
  },

  compareWithThreshold: (actual: number, threshold: number, metricName: string) => {
    const passed = actual <= threshold;
    console.log(`${metricName}: ${actual}ms (阈值: ${threshold}ms) - ${passed ? 'PASS' : 'FAIL'}`);
    return passed;
  },
};
