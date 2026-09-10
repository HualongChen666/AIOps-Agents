'use client';

import { useMemo, useState } from 'react';
import { useLocale } from '@/lib/i18n';
import { getCompleteNavGroups } from '@/lib/nav';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Search } from 'lucide-react';

export default function AllFeaturesPage() {
  const { locale } = useLocale();
  const pathname = usePathname();
  const [searchQuery, setSearchQuery] = useState('');

  const navGroups = useMemo(() => getCompleteNavGroups(locale), [locale]);

  const filteredGroups = useMemo(() => {
    if (!searchQuery) return navGroups;

    const query = searchQuery.toLowerCase();
    return navGroups.map(group => ({
      ...group,
      items: group.items.filter(item =>
        item.label.toLowerCase().includes(query) ||
        item.href.toLowerCase().includes(query)
      )
    })).filter(group => group.items.length > 0);
  }, [navGroups, searchQuery]);

  const isActive = (href: string) => {
    if (href === '/') return pathname === '/';
    return pathname.startsWith(href);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">全部功能</h1>
        <p className="text-sm text-gray-500 mt-1">查看所有可用功能</p>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              placeholder="搜索功能..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      <div className="space-y-6">
        {filteredGroups.map((group) => (
          <Card key={group.title}>
            <CardHeader>
              <CardTitle className="text-lg">{group.title}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {group.items.map((item) =>
                  item.href.startsWith('http') ? (
                    <a
                      key={item.href}
                      href={item.href}
                      target={item.target}
                      rel="noopener noreferrer"
                      className="p-3 border rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      <div className="font-medium">{item.label}</div>
                      <div className="text-xs text-gray-500 mt-1">外部链接</div>
                    </a>
                  ) : (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`p-3 border rounded-lg transition-colors ${isActive(item.href)
                          ? 'bg-blue-50 border-blue-500'
                          : 'hover:bg-gray-50'
                        }`}
                    >
                      <div className="font-medium">{item.label}</div>
                      <div className="text-xs text-gray-500 mt-1">{item.href}</div>
                    </Link>
                  )
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
