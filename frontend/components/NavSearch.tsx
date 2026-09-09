'use client';

import { useState, useEffect, useCallback } from 'react';
import { Input } from '@/components/ui/input';
import { getNavGroups, type NavItem } from '@/lib/nav';
import { useLocale } from '@/lib/i18n';
import { usePathname, useRouter } from 'next/navigation';
import { Search, Clock, X } from 'lucide-react';

export function NavSearch() {
  const { locale } = useLocale();
  const pathname = usePathname();
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [results, setResults] = useState<NavItem[]>([]);
  const [searchHistory, setSearchHistory] = useState<string[]>([]);

  const navGroups = getNavGroups(locale);

  // 从localStorage加载搜索历史
  useEffect(() => {
    try {
      const history = localStorage.getItem('nav-search-history');
      if (history) {
        setSearchHistory(JSON.parse(history));
      }
    } catch {
      setSearchHistory([]);
    }
  }, []);

  // 保存搜索历史
  const saveSearchHistory = useCallback((query: string) => {
    if (!query.trim()) return;

    const newHistory = [query, ...searchHistory.filter(h => h !== query)].slice(0, 5);
    setSearchHistory(newHistory);
    localStorage.setItem('nav-search-history', JSON.stringify(newHistory));
  }, [searchHistory]);

  // 搜索功能
  const handleSearch = useCallback((q: string) => {
    setQuery(q);

    if (!q.trim()) {
      setResults([]);
      return;
    }

    const queryLower = q.toLowerCase();
    const allItems: NavItem[] = navGroups.flatMap(group => group.items);

    const filtered = allItems.filter(item =>
      item.label.toLowerCase().includes(queryLower) ||
      item.href.toLowerCase().includes(queryLower)
    );

    setResults(filtered.slice(0, 10));
  }, [navGroups]);

  // 快捷键支持
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen(true);
      }
      if (e.key === 'Escape') {
        setIsOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // 点击外部关闭
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest('.nav-search-container')) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  const handleItemClick = (item: NavItem) => {
    saveSearchHistory(query);
    setQuery('');
    setResults([]);
    setIsOpen(false);
    router.push(item.href);
  };

  const handleHistoryClick = (historyItem: string) => {
    setQuery(historyItem);
    handleSearch(historyItem);
  };

  const clearHistory = () => {
    setSearchHistory([]);
    localStorage.removeItem('nav-search-history');
  };

  return (
    <div className="nav-search-container relative">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
        <Input
          placeholder="搜索功能... (Ctrl+K)"
          value={query}
          onChange={(e) => handleSearch(e.target.value)}
          onFocus={() => setIsOpen(true)}
          className="pl-10"
        />
      </div>

      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-white border rounded-lg shadow-lg z-50 max-h-96 overflow-y-auto">
          {query.trim() ? (
            // 搜索结果
            results.length > 0 ? (
              <div className="p-2">
                {results.map((item) => (
                  <button
                    key={item.href}
                    onClick={() => handleItemClick(item)}
                    className={`w-full text-left px-3 py-2 rounded hover:bg-gray-100 transition-colors ${
                      pathname === item.href ? 'bg-blue-50 text-blue-600' : ''
                    }`}
                  >
                    <div className="font-medium">{item.label}</div>
                    <div className="text-xs text-gray-500">{item.href}</div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="p-4 text-center text-gray-500">
                未找到匹配的功能
              </div>
            )
          ) : (
            // 搜索历史
            searchHistory.length > 0 && (
              <div className="p-2">
                <div className="flex items-center justify-between px-3 py-2">
                  <div className="flex items-center gap-2 text-sm text-gray-500">
                    <Clock className="h-4 w-4" />
                    <span>搜索历史</span>
                  </div>
                  <button
                    onClick={clearHistory}
                    className="text-xs text-gray-400 hover:text-gray-600"
                  >
                    清除
                  </button>
                </div>
                {searchHistory.map((historyItem, index) => (
                  <button
                    key={index}
                    onClick={() => handleHistoryClick(historyItem)}
                    className="w-full text-left px-3 py-2 rounded hover:bg-gray-100 transition-colors text-sm"
                  >
                    {historyItem}
                  </button>
                ))}
              </div>
            )
          )}
        </div>
      )}
    </div>
  );
}
