#!/usr/bin/env node

/**
 * 模块化覆盖率测试脚本
 * 分模块运行测试以避免内存溢出
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const TEST_MODULES = [
  {
    name: 'pages',
    pattern: '__tests__/pages/**/*.test.tsx',
    description: '核心页面测试'
  },
  {
    name: 'components-ui',
    pattern: '__tests__/components/ui/**/*.test.tsx',
    description: 'UI组件测试'
  },
  {
    name: 'components-business',
    pattern: '__tests__/components/business/**/*.test.tsx',
    description: '业务组件测试'
  },
  {
    name: 'components-charts',
    pattern: '__tests__/components/charts/**/*.test.tsx',
    description: '图表组件测试'
  },
  {
    name: 'components-layout',
    pattern: '__tests__/components/layout/**/*.test.tsx',
    description: '布局组件测试'
  },
  {
    name: 'routing',
    pattern: '__tests__/routing/**/*.test.tsx',
    description: '路由测试'
  },
  {
    name: 'store',
    pattern: '__tests__/store/**/*.test.ts',
    description: '状态管理测试'
  },
  {
    name: 'hooks',
    pattern: '__tests__/hooks/**/*.test.ts',
    description: 'Hooks测试'
  },
  {
    name: 'forms',
    pattern: '__tests__/forms/**/*.test.tsx',
    description: '表单测试'
  },
  {
    name: 'accessibility',
    pattern: '__tests__/accessibility/**/*.test.tsx',
    description: '可访问性测试'
  },
  {
    name: 'performance',
    pattern: '__tests__/performance/**/*.test.tsx',
    description: '性能测试'
  },
];

const RESULTS_DIR = path.join(__dirname, 'coverage-module-results');
const COVERAGE_DIR = path.join(__dirname, 'coverage');

// 创建结果目录
if (!fs.existsSync(RESULTS_DIR)) {
  fs.mkdirSync(RESULTS_DIR, { recursive: true });
}

// 清理旧的覆盖率数据
if (fs.existsSync(COVERAGE_DIR)) {
  fs.rmSync(COVERAGE_DIR, { recursive: true, force: true });
}

console.log('🧪 开始模块化覆盖率测试...\n');

const results = [];

for (const module of TEST_MODULES) {
  console.log(`\n📦 测试模块: ${module.name} (${module.description})`);
  console.log(`   模式: ${module.pattern}`);

  try {
    const startTime = Date.now();

    // 运行测试并生成覆盖率
    const command = `node --max-old-space-size=4096 node_modules/.bin/jest "${module.pattern}" --coverage --coverageDirectory="${RESULTS_DIR}/${module.name}" --maxWorkers=1 --no-cache`;

    execSync(command, {
      stdio: 'inherit',
      cwd: __dirname,
      timeout: 300000 // 5分钟超时
    });

    const duration = (Date.now() - startTime) / 1000;

    results.push({
      module: module.name,
      status: 'success',
      duration: duration
    });

    console.log(`   ✅ 成功 (${duration.toFixed(2)}s)`);

  } catch (error) {
    results.push({
      module: module.name,
      status: 'failed',
      error: error.message
    });

    console.log(`   ❌ 失败: ${error.message}`);
  }
}

// 生成汇总报告
console.log('\n\n📊 测试结果汇总:\n');
console.log('='.repeat(60));

let successCount = 0;
let failCount = 0;

for (const result of results) {
  if (result.status === 'success') {
    successCount++;
    console.log(`✅ ${result.module.padEnd(25)} ${result.duration?.toFixed(2) + 's'.padEnd(10)}`);
  } else {
    failCount++;
    console.log(`❌ ${result.module.padEnd(25)} FAILED`);
  }
}

console.log('='.repeat(60));
console.log(`总计: ${results.length} 个模块`);
console.log(`成功: ${successCount} 个`);
console.log(`失败: ${failCount} 个`);

if (failCount > 0) {
  console.log('\n⚠️  部分模块测试失败，请检查日志');
  process.exit(1);
} else {
  console.log('\n🎉 所有模块测试完成！');
  console.log(`\n覆盖率报告保存在: ${RESULTS_DIR}`);
  console.log('使用以下命令查看各个模块的覆盖率:');
  TEST_MODULES.forEach(module => {
    console.log(`  npx http-server ${RESULTS_DIR}/${module.name}`);
  });
}