'use client';

import '@/styles/globals.css';
import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { Providers } from './providers';
import { SideNav } from '@/components/SideNav';
import { TopBar } from '@/components/TopBar';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { isAuthenticated } from '@/lib/api';
import type { ReactNode } from 'react';

const PUBLIC_PATHS = ['/login', '/setup'];

function useAuthGuard() {
  const pathname = usePathname();
  const router = useRouter();
  const [authed, setAuthed] = useState<boolean | null>(null);

  useEffect(() => {
    const v = isAuthenticated();
    const isPublic = PUBLIC_PATHS.includes(pathname);
    if (!v && !isPublic) {
      router.replace('/login');
    } else if (v && isPublic) {
      router.replace('/');
    }
    setAuthed(v);
  }, [pathname, router]);

  return authed;
}

function LoadingShell() {
  return (
    <html lang="zh-CN">
      <head>
        <title>AIOps Agent 控制台</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body className="h-screen overflow-hidden bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 text-gray-900 flex items-center justify-center">
        <div className="loading-spinner"></div>
        <div className="ml-3 text-base text-gray-600 font-medium">加载中...</div>
      </body>
    </html>
  );
}

export default function RootLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isPublic = PUBLIC_PATHS.includes(pathname);
  const authed = useAuthGuard();

  if (authed === null) {
    return <LoadingShell />;
  }

  if (!isPublic && !authed) {
    return <LoadingShell />;
  }

  if (isPublic && authed) {
    return <LoadingShell />;
  }

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
                    {children}
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
                      {children}
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
