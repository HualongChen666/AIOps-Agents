// app/layout.tsx
import '@/styles/globals.css';
import { Providers } from './providers';
import type { ReactNode } from 'react';

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <title>AIOps Agent 控制台</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body className="font-sans">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
