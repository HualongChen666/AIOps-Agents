'use client';

import '@/styles/globals.css';
import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { Providers } from './providers';
import { SideNav } from '@/components/SideNav';
import { isAuthenticated } from '@/lib/api';
import type { ReactNode } from 'react';

const PUBLIC_PATHS = ['/login', '/setup'];

function useAuthGuard() {
  const pathname = usePathname();
  const router = useRouter();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const authed = isAuthenticated();
    const isPublic = PUBLIC_PATHS.includes(pathname);
    if (!authed && !isPublic) {
      router.replace('/login');
    } else if (authed && isPublic) {
      router.replace('/');
    }
    setChecked(true);
  }, [pathname, router]);

  return checked;
}

export default function RootLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isPublic = PUBLIC_PATHS.includes(pathname);
  const checked = useAuthGuard();

  if (!checked) {
    return (
      <html lang="en" className="dark">
        <head>
          <title>AIOps Agent 控制台</title>
          <meta name="viewport" content="width=device-width, initial-scale=1" />
        </head>
        <body className="h-screen overflow-hidden bg-[var(--dds-slate-10)] text-[var(--dds-gray-90)]" />
      </html>
    );
  }

  return (
    <html lang="en" className="dark">
      <head>
        <title>AIOps Agent 控制台</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body className="h-screen overflow-hidden bg-[var(--dds-slate-10)] text-[var(--dds-gray-90)]">
        <Providers>
          <div className="flex h-full">
            {!isPublic && <SideNav />}
            <main className={`flex-1 h-full overflow-y-auto main-scroll bg-[var(--dds-gray-10)] ${isPublic ? 'w-full' : ''}`}>
              <div className="min-h-full p-8">
                {children}
              </div>
            </main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
