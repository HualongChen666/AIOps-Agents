// app/layout.tsx — DDS 风格左右分栏布局
import '@/styles/globals.css';
import { Providers } from './providers';
import { SideNav } from '@/components/SideNav';
import type { ReactNode } from 'react';

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <title>AIOps Agent 控制台</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body className="h-screen overflow-hidden bg-[var(--dds-slate-10)] text-[var(--dds-gray-90)]">
        <Providers>
          <div className="flex h-full">
            <SideNav />
            <main className="flex-1 h-full overflow-y-auto main-scroll bg-[var(--dds-gray-10)]">
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
