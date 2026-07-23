'use client'

import Link from 'next/link';
import { usePathname } from 'next/navigation';

interface NavItem {
  href: string;
  label: string;
  icon?: string;
}

const navItems: NavItem[] = [
  { href: '/dashboard', label: '仪表盘', icon: '📊' },
  { href: '/alerts', label: '告警', icon: '🔔' },
  { href: '/topology', label: '拓扑', icon: '🔗' },
  { href: '/anomaly', label: '分析', icon: '📈' },
  { href: '/auto-heal', label: '修复', icon: '🔧' },
  { href: '/capacity', label: '容量', icon: '💾' },
  { href: '/cost', label: '成本', icon: '💰' },
  { href: '/kpi', label: '监控', icon: '📡' },
  { href: '/settings', label: '设置', icon: '⚙️' },
];

export const Sidebar = () => {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-gray-900 text-white flex flex-col h-full">
      <div className="p-6 border-b border-gray-700">
        <h1 className="text-xl font-bold flex items-center gap-2">
          <span className="text-2xl">🤖</span>
          AIOps Agent
        </h1>
      </div>
      
      <nav className="flex-1 p-4 space-y-2">
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                isActive
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              }`}
            >
              <span className="text-lg">{item.icon}</span>
              <span className="font-medium">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-gray-700">
        <div className="flex items-center gap-3 px-4 py-2">
          <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-sm font-bold">
            U
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium">用户</p>
            <p className="text-xs text-gray-400">管理员</p>
          </div>
        </div>
      </div>
    </aside>
  );
};
