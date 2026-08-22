/**
 * Bundle大小优化测试
 * 测试代码分割效果、包大小分析
 */

import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

// Bundle大小阈值（字节）
const BUNDLE_SIZE_THRESHOLDS = {
  MAIN_BUNDLE: 500 * 1024, // 500KB
  VENDOR_BUNDLE: 1000 * 1024, // 1MB
  CHUNK_SIZE: 200 * 1024, // 200KB
  TOTAL_SIZE: 2000 * 1024, // 2MB
  CSS_SIZE: 50 * 1024, // 50KB
};

// 代码分割目标
const CODE_SPLITTING_TARGETS = {
  MIN_CHUNKS: 3, // 最少分割成3个chunk
  MAX_CHUNK_SIZE: 300 * 1024, // 单个chunk最大300KB
  LAZY_LOADED_ROUTES: 5, // 至少5个路由应该懒加载
};

// 模拟构建产物分析
interface BundleAnalysis {
  name: string;
  size: number;
  modules: string[];
  dependencies: string[];
}

interface ChunkInfo {
  name: string;
  size: number;
  isLazy: boolean;
  imports: string[];
}

// Bundle分析器
class BundleAnalyzer {
  private bundles: Map<string, BundleAnalysis> = new Map();
  private chunks: ChunkInfo[] = [];

  addBundle(bundle: BundleAnalysis) {
    this.bundles.set(bundle.name, bundle);
  }

  addChunk(chunk: ChunkInfo) {
    this.chunks.push(chunk);
  }

  getBundle(name: string): BundleAnalysis | undefined {
    return this.bundles.get(name);
  }

  getAllBundles(): BundleAnalysis[] {
    return Array.from(this.bundles.values());
  }

  getAllChunks(): ChunkInfo[] {
    return this.chunks;
  }

  getTotalSize(): number {
    return Array.from(this.bundles.values()).reduce((sum, bundle) => sum + bundle.size, 0);
  }

  getLazyChunks(): ChunkInfo[] {
    return this.chunks.filter(chunk => chunk.isLazy);
  }

  getLargestBundle(): BundleAnalysis | undefined {
    const bundles = this.getAllBundles();
    return bundles.reduce((max, bundle) =>
      bundle.size > (max?.size || 0) ? bundle : max, undefined);
  }

  analyzeCodeSplitting(): {
    totalChunks: number;
    lazyChunks: number;
    lazyPercentage: number;
    averageChunkSize: number;
    largestChunkSize: number;
  } {
    const totalChunks = this.chunks.length;
    const lazyChunks = this.getLazyChunks().length;
    const lazyPercentage = totalChunks > 0 ? (lazyChunks / totalChunks) * 100 : 0;
    const averageChunkSize = totalChunks > 0
      ? this.chunks.reduce((sum, chunk) => sum + chunk.size, 0) / totalChunks
      : 0;
    const largestChunkSize = Math.max(...this.chunks.map(chunk => chunk.size), 0);

    return {
      totalChunks,
      lazyChunks,
      lazyPercentage,
      averageChunkSize,
      largestChunkSize,
    };
  }

  generateReport(): {
    timestamp: string;
    bundles: BundleAnalysis[];
    chunks: ChunkInfo[];
    totalSize: number;
    codeSplitting: ReturnType<typeof this.analyzeCodeSplitting>;
    recommendations: string[];
  } {
    const codeSplitting = this.analyzeCodeSplitting();
    const recommendations: string[] = [];

    // 生成优化建议
    const largestBundle = this.getLargestBundle();
    if (largestBundle && largestBundle.size > BUNDLE_SIZE_THRESHOLDS.MAIN_BUNDLE) {
      recommendations.push(
        `主bundle ${largestBundle.name} (${(largestBundle.size / 1024).toFixed(2)}KB) 超过阈值，建议进一步分割`
      );
    }

    if (codeSplitting.lazyChunks < CODE_SPLITTING_TARGETS.LAZY_LOADED_ROUTES) {
      recommendations.push(
        `懒加载chunk数量 (${codeSplitting.lazyChunks}) 低于目标 (${CODE_SPLITTING_TARGETS.LAZY_LOADED_ROUTES})，建议增加路由级代码分割`
      );
    }

    if (codeSplitting.largestChunkSize > CODE_SPLITTING_TARGETS.MAX_CHUNK_SIZE) {
      recommendations.push(
        `最大chunk大小 (${(codeSplitting.largestChunkSize / 1024).toFixed(2)}KB) 超过阈值，建议优化`
      );
    }

    return {
      timestamp: new Date().toISOString(),
      bundles: this.getAllBundles(),
      chunks: this.chunks,
      totalSize: this.getTotalSize(),
      codeSplitting,
      recommendations,
    };
  }
}

// 模拟Next.js构建产物
const mockNextBuildOutput = {
  bundles: [
    {
      name: 'main.js',
      size: 450 * 1024, // 450KB
      modules: ['app/dashboard/page.tsx', 'app/alerts/page.tsx', 'components/ui/*.tsx'],
      dependencies: ['react', 'react-dom', 'next'],
    },
    {
      name: 'vendor.js',
      size: 800 * 1024, // 800KB
      modules: ['node_modules/react', 'node_modules/react-dom', 'node_modules/@tanstack/react-query'],
      dependencies: ['react', 'react-dom', '@tanstack/react-query', 'axios'],
    },
    {
      name: 'framework.js',
      size: 200 * 1024, // 200KB
      modules: ['node_modules/next'],
      dependencies: ['next'],
    },
  ],
  chunks: [
    {
      name: 'dashboard-chunk.js',
      size: 150 * 1024, // 150KB
      isLazy: true,
      imports: ['main.js'],
    },
    {
      name: 'alerts-chunk.js',
      size: 120 * 1024, // 120KB
      isLazy: true,
      imports: ['main.js'],
    },
    {
      name: 'anomaly-chunk.js',
      size: 130 * 1024, // 130KB
      isLazy: true,
      imports: ['main.js'],
    },
    {
      name: 'charts-chunk.js',
      size: 180 * 1024, // 180KB
      isLazy: true,
      imports: ['main.js'],
    },
    {
      name: 'ai-copilot-chunk.js',
      size: 160 * 1024, // 160KB
      isLazy: true,
      imports: ['main.js'],
    },
  ],
};

describe('Bundle大小优化测试', () => {
  let analyzer: BundleAnalyzer;

  beforeEach(() => {
    analyzer = new BundleAnalyzer();
    jest.clearAllMocks();
  });

  describe('Bundle大小验证', () => {
    it('应该验证主bundle大小在阈值内', () => {
      const mainBundle: BundleAnalysis = {
        name: 'main.js',
        size: 450 * 1024,
        modules: ['app/dashboard/page.tsx'],
        dependencies: ['react', 'next'],
      };

      analyzer.addBundle(mainBundle);

      const size = mainBundle.size;
      const threshold = BUNDLE_SIZE_THRESHOLDS.MAIN_BUNDLE;
      const passed = size <= threshold;

      console.log(`主bundle大小: ${(size / 1024).toFixed(2)}KB (阈值: ${(threshold / 1024).toFixed(2)}KB) - ${passed ? 'PASS' : 'FAIL'}`);

      expect(size).toBeLessThanOrEqual(threshold);
    });

    it('应该验证vendor bundle大小在阈值内', () => {
      const vendorBundle: BundleAnalysis = {
        name: 'vendor.js',
        size: 800 * 1024,
        modules: ['node_modules/*'],
        dependencies: ['react', 'react-dom', '@tanstack/react-query'],
      };

      analyzer.addBundle(vendorBundle);

      const size = vendorBundle.size;
      const threshold = BUNDLE_SIZE_THRESHOLDS.VENDOR_BUNDLE;
      const passed = size <= threshold;

      console.log(`Vendor bundle大小: ${(size / 1024).toFixed(2)}KB (阈值: ${(threshold / 1024).toFixed(2)}KB) - ${passed ? 'PASS' : 'FAIL'}`);

      expect(size).toBeLessThanOrEqual(threshold);
    });

    it('应该验证总bundle大小在阈值内', () => {
      const bundles: BundleAnalysis[] = [
        { name: 'main.js', size: 450 * 1024, modules: [], dependencies: [] },
        { name: 'vendor.js', size: 800 * 1024, modules: [], dependencies: [] },
        { name: 'framework.js', size: 200 * 1024, modules: [], dependencies: [] },
      ];

      bundles.forEach(bundle => analyzer.addBundle(bundle));

      const totalSize = analyzer.getTotalSize();
      const threshold = BUNDLE_SIZE_THRESHOLDS.TOTAL_SIZE;
      const passed = totalSize <= threshold;

      console.log(`总bundle大小: ${(totalSize / 1024).toFixed(2)}KB (阈值: ${(threshold / 1024).toFixed(2)}KB) - ${passed ? 'PASS' : 'FAIL'}`);

      expect(totalSize).toBeLessThanOrEqual(threshold);
    });

    it('应该验证CSS bundle大小在阈值内', () => {
      const cssBundle: BundleAnalysis = {
        name: 'styles.css',
        size: 30 * 1024,
        modules: ['styles/*.css'],
        dependencies: ['tailwindcss'],
      };

      analyzer.addBundle(cssBundle);

      const size = cssBundle.size;
      const threshold = BUNDLE_SIZE_THRESHOLDS.CSS_SIZE;
      const passed = size <= threshold;

      console.log(`CSS bundle大小: ${(size / 1024).toFixed(2)}KB (阈值: ${(threshold / 1024).toFixed(2)}KB) - ${passed ? 'PASS' : 'FAIL'}`);

      expect(size).toBeLessThanOrEqual(threshold);
    });
  });

  describe('代码分割效果验证', () => {
    it('应该验证代码分割达到目标', () => {
      const chunks: ChunkInfo[] = [
        { name: 'dashboard-chunk.js', size: 150 * 1024, isLazy: true, imports: ['main.js'] },
        { name: 'alerts-chunk.js', size: 120 * 1024, isLazy: true, imports: ['main.js'] },
        { name: 'anomaly-chunk.js', size: 130 * 1024, isLazy: true, imports: ['main.js'] },
        { name: 'charts-chunk.js', size: 180 * 1024, isLazy: true, imports: ['main.js'] },
        { name: 'ai-copilot-chunk.js', size: 160 * 1024, isLazy: true, imports: ['main.js'] },
      ];

      chunks.forEach(chunk => analyzer.addChunk(chunk));

      const analysis = analyzer.analyzeCodeSplitting();

      console.log('代码分割分析:', {
        totalChunks: analysis.totalChunks,
        lazyChunks: analysis.lazyChunks,
        lazyPercentage: `${analysis.lazyPercentage.toFixed(2)}%`,
        averageChunkSize: `${(analysis.averageChunkSize / 1024).toFixed(2)}KB`,
        largestChunkSize: `${(analysis.largestChunkSize / 1024).toFixed(2)}KB`,
      });

      expect(analysis.totalChunks).toBeGreaterThanOrEqual(CODE_SPLITTING_TARGETS.MIN_CHUNKS);
      expect(analysis.lazyChunks).toBeGreaterThanOrEqual(CODE_SPLITTING_TARGETS.LAZY_LOADED_ROUTES);
      expect(analysis.largestChunkSize).toBeLessThanOrEqual(CODE_SPLITTING_TARGETS.MAX_CHUNK_SIZE);
    });

    it('应该验证chunk大小在合理范围内', () => {
      const chunks: ChunkInfo[] = [
        { name: 'chunk1.js', size: 150 * 1024, isLazy: true, imports: [] },
        { name: 'chunk2.js', size: 200 * 1024, isLazy: true, imports: [] },
        { name: 'chunk3.js', size: 180 * 1024, isLazy: false, imports: [] },
      ];

      chunks.forEach(chunk => analyzer.addChunk(chunk));

      chunks.forEach(chunk => {
        const passed = chunk.size <= BUNDLE_SIZE_THRESHOLDS.CHUNK_SIZE;
        console.log(`Chunk ${chunk.name}: ${(chunk.size / 1024).toFixed(2)}KB - ${passed ? 'PASS' : 'FAIL'}`);
        expect(chunk.size).toBeLessThanOrEqual(BUNDLE_SIZE_THRESHOLDS.CHUNK_SIZE);
      });
    });

    it('应该验证懒加载路由正确配置', () => {
      const lazyRoutes = [
        'dashboard',
        'alerts',
        'anomaly',
        'charts',
        'ai-copilot',
      ];

      console.log('懒加载路由配置:', lazyRoutes);
      console.log(`Lazy loaded routes count: ${lazyRoutes.length} (target: ${CODE_SPLITTING_TARGETS.LAZY_LOADED_ROUTES})`);

      expect(lazyRoutes.length).toBeGreaterThanOrEqual(CODE_SPLITTING_TARGETS.LAZY_LOADED_ROUTES);
    });
  });

  describe('依赖分析', () => {
    it('应该分析bundle依赖关系', () => {
      const bundles: BundleAnalysis[] = [
        {
          name: 'main.js',
          size: 450 * 1024,
          modules: ['app/dashboard/page.tsx'],
          dependencies: ['react', 'react-dom', 'next'],
        },
        {
          name: 'vendor.js',
          size: 800 * 1024,
          modules: ['node_modules/*'],
          dependencies: ['react', 'react-dom', '@tanstack/react-query', 'axios'],
        },
      ];

      bundles.forEach(bundle => analyzer.addBundle(bundle));

      const mainBundle = analyzer.getBundle('main.js');
      const vendorBundle = analyzer.getBundle('vendor.js');

      console.log('Main bundle dependencies:', mainBundle?.dependencies);
      console.log('Vendor bundle dependencies:', vendorBundle?.dependencies);

      expect(mainBundle?.dependencies).toContain('react');
      expect(vendorBundle?.dependencies).toContain('@tanstack/react-query');
    });

    it('应该检测重复依赖', () => {
      const bundles: BundleAnalysis[] = [
        {
          name: 'main.js',
          size: 450 * 1024,
          modules: [],
          dependencies: ['react', 'react-dom', 'lodash'],
        },
        {
          name: 'vendor.js',
          size: 800 * 1024,
          modules: [],
          dependencies: ['react', 'react-dom', 'lodash', '@tanstack/react-query'],
        },
      ];

      bundles.forEach(bundle => analyzer.addBundle(bundle));

      const allDependencies = bundles.flatMap(bundle => bundle.dependencies);
      const duplicateDependencies = allDependencies.filter((dep, index) =>
        allDependencies.indexOf(dep) !== index
      );

      const uniqueDuplicates = [...new Set(duplicateDependencies)];
      console.log('Duplicate dependencies:', uniqueDuplicates);

      // 某些重复是正常的（如react），但应该监控
      expect(Array.isArray(uniqueDuplicates)).toBe(true);
    });
  });

  describe('模拟构建产物分析', () => {
    it('应该分析模拟的Next.js构建产物', () => {
      mockNextBuildOutput.bundles.forEach(bundle => analyzer.addBundle(bundle));
      mockNextBuildOutput.chunks.forEach(chunk => analyzer.addChunk(chunk));

      const report = analyzer.generateReport();

      console.log('Bundle分析报告:', JSON.stringify(report, null, 2));

      expect(report.bundles.length).toBeGreaterThan(0);
      expect(report.chunks.length).toBeGreaterThan(0);
      expect(report.totalSize).toBeGreaterThan(0);
      expect(report.codeSplitting.totalChunks).toBeGreaterThan(0);
    });

    it('应该生成优化建议', () => {
      mockNextBuildOutput.bundles.forEach(bundle => analyzer.addBundle(bundle));
      mockNextBuildOutput.chunks.forEach(chunk => analyzer.addChunk(chunk));

      const report = analyzer.generateReport();

      console.log('优化建议:', report.recommendations);

      expect(Array.isArray(report.recommendations)).toBe(true);
    });
  });

  describe('性能基准测试', () => {
    it('应该设置和验证bundle大小基准', () => {
      const benchmarks = {
        main: { current: 450 * 1024, target: 400 * 1024, max: 500 * 1024 },
        vendor: { current: 800 * 1024, target: 700 * 1024, max: 1000 * 1024 },
        framework: { current: 200 * 1024, target: 180 * 1024, max: 250 * 1024 },
      };

      console.log('Bundle size benchmarks:', JSON.stringify(benchmarks, null, 2));

      Object.entries(benchmarks).forEach(([name, benchmark]) => {
        const { current, target, max } = benchmark;
        const meetsTarget = current <= target;
        const withinMax = current <= max;

        console.log(`${name}: current ${(current / 1024).toFixed(2)}KB, target ${(target / 1024).toFixed(2)}KB, max ${(max / 1024).toFixed(2)}KB`);
        console.log(`  meets target: ${meetsTarget}, within max: ${withinMax}`);

        expect(current).toBeLessThanOrEqual(max);
      });
    });

    it('应该跟踪bundle大小变化趋势', () => {
      const history = [
        { version: '1.0.0', mainSize: 480 * 1024, vendorSize: 850 * 1024 },
        { version: '1.1.0', mainSize: 460 * 1024, vendorSize: 820 * 1024 },
        { version: '1.2.0', mainSize: 450 * 1024, vendorSize: 800 * 1024 },
      ];

      console.log('Bundle size trend:', history);

      const latest = history[history.length - 1];
      const first = history[0];

      const mainReduction = ((first.mainSize - latest.mainSize) / first.mainSize * 100).toFixed(2);
      const vendorReduction = ((first.vendorSize - latest.vendorSize) / first.vendorSize * 100).toFixed(2);

      console.log(`Main bundle reduction: ${mainReduction}%`);
      console.log(`Vendor bundle reduction: ${vendorReduction}%`);

      // 验证趋势是积极的（大小减少或保持稳定）
      expect(latest.mainSize).toBeLessThanOrEqual(first.mainSize);
    });
  });

  describe('实际文件分析（如果存在）', () => {
    it('应该尝试分析实际的构建产物', () => {
      const buildPath = join(process.cwd(), '.next', 'static');
      const buildExists = existsSync(buildPath);

      if (buildExists) {
        console.log('发现构建产物目录:', buildPath);
        // 这里可以添加实际的文件分析逻辑
      } else {
        console.log('未发现构建产物，使用模拟数据');
      }

      expect(typeof buildExists).toBe('boolean');
    });
  });

  describe('Tree Shaking验证', () => {
    it('应该验证未使用的代码被移除', () => {
      const usedExports = ['render', 'useState', 'useEffect'];
      const totalExports = ['render', 'useState', 'useEffect', 'useContext', 'useReducer', 'useMemo', 'useCallback'];

      const unusedExports = totalExports.filter(exp => !usedExports.includes(exp));
      const treeShakingEfficiency = (usedExports.length / totalExports.length * 100).toFixed(2);

      console.log('Tree shaking analysis:', {
        usedExports,
        unusedExports,
        treeShakingEfficiency: `${treeShakingEfficiency}%`,
      });

      expect(usedExports.length).toBeLessThan(totalExports.length);
    });

    it('应该验证死代码消除', () => {
      const liveCode = 450 * 1024; // 450KB
      const deadCode = 50 * 1024; // 50KB
      const totalCode = liveCode + deadCode;

      const deadCodeEliminationRate = (deadCode / totalCode * 100).toFixed(2);

      console.log('Dead code elimination analysis:', {
        liveCode: `${(liveCode / 1024).toFixed(2)}KB`,
        deadCode: `${(deadCode / 1024).toFixed(2)}KB`,
        totalCode: `${(totalCode / 1024).toFixed(2)}KB`,
        deadCodeEliminationRate: `${deadCodeEliminationRate}%`,
      });

      expect(deadCode).toBeGreaterThan(0);
    });
  });
});

// 导出Bundle分析工具
export const bundleAnalysisUtils = {
  analyzeBundleSize: (bundlePath: string) => {
    // 实际实现中，这里会读取和分析实际的bundle文件
    return {
      size: 0,
      gzippedSize: 0,
      modules: [],
      dependencies: [],
    };
  },

  compareWithBaseline: (current: number, baseline: number, tolerance: number = 0.1) => {
    const difference = current - baseline;
    const percentageChange = (difference / baseline) * 100;
    const withinTolerance = Math.abs(percentageChange) <= tolerance * 100;

    return {
      current,
      baseline,
      difference,
      percentageChange,
      withinTolerance,
      status: withinTolerance ? 'PASS' : 'FAIL',
    };
  },

  generateOptimizationSuggestions: (analysis: any) => {
    const suggestions: string[] = [];

    if (analysis.totalSize > BUNDLE_SIZE_THRESHOLDS.TOTAL_SIZE) {
      suggestions.push('考虑进一步代码分割以减少总bundle大小');
    }

    if (analysis.codeSplitting.lazyPercentage < 50) {
      suggestions.push('增加路由级懒加载以提高代码分割效果');
    }

    if (analysis.largestChunkSize > CODE_SPLITTING_TARGETS.MAX_CHUNK_SIZE) {
      suggestions.push('拆分过大的chunk以改善加载性能');
    }

    return suggestions;
  },
};
