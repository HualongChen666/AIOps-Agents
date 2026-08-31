'use client'

import { useEffect } from 'react'
import { useAuthStore } from '@/store/auth'
import { useRouter } from 'next/navigation'
import { Card, CardContent } from '@/components/ui/card'
import { Shield, Lock } from 'lucide-react'

interface AuthorizationGuardProps {
  children: React.ReactNode
  requiredPermission?: string
  requiredRole?: string
  fallback?: React.ReactNode
}

export function AuthorizationGuard({
  children,
  requiredPermission,
  requiredRole,
  fallback,
}: AuthorizationGuardProps) {
  const { user, isAuthenticated, hasPermission, hasRole } = useAuthStore()
  const router = useRouter()

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, router])

  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6">
            <div className="flex flex-col items-center gap-4 text-center">
              <Lock className="h-12 w-12 text-gray-400" />
              <div>
                <h3 className="text-lg font-semibold">需要登录</h3>
                <p className="text-sm text-gray-500">请登录以访问此页面</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (requiredRole && !hasRole(requiredRole)) {
    if (fallback) return <>{fallback}</>
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6">
            <div className="flex flex-col items-center gap-4 text-center">
              <Shield className="h-12 w-12 text-yellow-500" />
              <div>
                <h3 className="text-lg font-semibold">权限不足</h3>
                <p className="text-sm text-gray-500">您需要 {requiredRole} 角色才能访问此页面</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (requiredPermission && !hasPermission(requiredPermission)) {
    if (fallback) return <>{fallback}</>
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6">
            <div className="flex flex-col items-center gap-4 text-center">
              <Shield className="h-12 w-12 text-red-500" />
              <div>
                <h3 className="text-lg font-semibold">权限不足</h3>
                <p className="text-sm text-gray-500">您需要 {requiredPermission} 权限才能访问此页面</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return <>{children}</>
}
