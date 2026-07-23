// app/page.tsx – 首页入口
import Link from 'next/link';

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100">
      <h1 className="text-4xl font-bold mb-4">AIOps Agent 控制台</h1>
      <p className="mb-6">企业级 AI 运维监控平台</p>
      <div className="space-x-4">
        <Link href="/overview" className="px-4 py-2 bg-primary text-white rounded hover:bg-primary/80 transition">
          总览仪表盘
        </Link>
        <Link href="/approval" className="px-4 py-2 bg-secondary text-white rounded hover:bg-secondary/80 transition">
          HITL 审批中心
        </Link>
        <Link href="/topology" className="px-4 py-2 bg-success text-white rounded hover:bg-success/80 transition">
          全链路拓扑
        </Link>
        <Link href="/workflow" className="px-4 py-2 bg-warning text-white rounded hover:bg-warning/80 transition">
          工作流可视化
        </Link>
        <Link href="/history" className="px-4 py-2 bg-danger text-white rounded hover:bg-danger/80 transition">
          RAG 历史搜索
        </Link>
      </div>
    </main>
  );
}
