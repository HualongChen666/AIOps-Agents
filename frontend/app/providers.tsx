'use client'

import { ReactNode, useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import { ThemeProvider } from '@/components/ThemeProvider'
import { LocaleProvider } from '@/lib/i18n'

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(() => new QueryClient())

  return (
    <ThemeProvider>
      <LocaleProvider>
        <QueryClientProvider client={queryClient}>
          {children}
          {/* Mount the toast host once so every page's react-hot-toast
              notifications are actually rendered (previously never mounted,
              so all toast.success/error calls were silently dropped). */}
          <Toaster position="top-right" />
        </QueryClientProvider>
      </LocaleProvider>
    </ThemeProvider>
  )
}
