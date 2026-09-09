'use client';

import '@/styles/globals.css';
import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { Providers } from './providers';
import { SideNav } from '@/components/SideNav';
import { TopBar } from '@/components/TopBar';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { isAuthenticated } from '@/lib/api';
import LoadingSpinner from '@/components/LoadingSpinner';
import type { ReactNode } from 'react';

const PUBLIC_PATHS = ['/login', '/setup'];

function useAuthGuard() {
  const pathname = usePathname();
  const router = useRouter();
  const [authed, setAuthed] = useState<boolean | null>(null);

  useEffect(() => {
    let mounted = true;
    // 把 isAuthenticated 调用包装为异步，以避免同步阻塞
    (async () => {
      try {
        const v = await Promise.resolve(isAuthenticated()); // 保留 isAuthenticated 实现不变的同时适配未来异步验证
        const isPublic = PUBLIC_PATHS.includes(pathname);
        if (!v && !isPublic) {
          // 等待认证状态确定后再导航，减少竞态
          router.replace('/login');
        } else if (v && isPublic) {
          router.replace('/');
        }
        if (mounted) setAuthed(Boolean(v));
      } catch (e) {
        if (mounted) setAuthed(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [pathname, router]);

  return authed;
}

export default function RootLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isPublic = PUBLIC_PATHS.includes(pathname);
  const authed = useAuthGuard();

  // 当 auth 尚未决定时，显示局部加载而不是返回整个 html
  const showLoading = authed === null || (!isPublic && !authed) || (isPublic && authed);

  return (
    <html lang="zh-CN">
      <head>
        <title>AIOps Agent 控制台</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body className="h-screen overflow-hidden bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 text-gray-900">
        <Providers>
          <ErrorBoundary>
            {isPublic ? (
              <div className="flex h-full">
                <main className="flex-1 h-full overflow-y-auto main-scroll bg-gray-50 w-full">
                  <div className="min-h-full p-8">
                    {showLoading ? <LoadingSpinner message="加载中..." /> : children}
                  </div>
                </main>
              </div>
            ) : (
              <div className="flex flex-col h-full">
                <TopBar />
                <div className="flex flex-1 overflow-hidden">
                  <SideNav />
                  <main className="flex-1 h-full overflow-y-auto main-scroll bg-gray-50">
                    <div className="min-h-full p-8">
                      {showLoading ? <LoadingSpinner message="加载中..." /> : children}
                    </div>
                  </main>
                </div>
              </div>
            )}
          </ErrorBoundary>
        </Providers>
      </body>
    </html>
  );
}
