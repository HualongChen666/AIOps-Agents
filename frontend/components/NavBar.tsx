'use client'

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ThemeToggle } from '@/components/ThemeToggle';

const navItems = [
  { href: '/overview', label: '总览' },
  { href: '/topology', label: '拓扑' },
  { href: '/workflow', label: '工作流' },
  { href: '/approval', label: '审批' },
  { href: '/history', label: '案例' },
  { href: '/audit', label: '审计' },
];

export const NavBar = () => {
  const pathname = usePathname();
  return (
    <nav className="bg-gray-100 dark:bg-gray-800 border-b border-gray-300 dark:border-gray-700 px-4 py-2 flex items-center justify-between">
      <div className="flex space-x-4">
        {navItems.map((item) => (
          <Link key={item.href} href={item.href} className={`px-3 py-1 rounded ${pathname.startsWith(item.href) ? 'bg-primary text-white' : 'text-gray-800 dark:text-gray-200 hover:bg-primary/20'}`}>
            {item.label}
          </Link>
        ))}
      </div>
      <ThemeToggle />
    </nav>
  );
};