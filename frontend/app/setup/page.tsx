'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export default function SetupPage() {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.post('/api/v1/auth/register-admin-bypass', { username, password });
      setDone(true);
    } catch (err: any) {
      setError(err?.response?.data?.detail || '创建管理员失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-center">创建首个管理员</CardTitle>
        </CardHeader>
        <CardContent>
          {done ? (
            <div className="space-y-4 text-center">
              <p className="text-green-600">管理员创建成功</p>
              <Link href="/login">
                <Button className="w-full">去登录</Button>
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">用户名</label>
                <Input required value={username} onChange={(e) => setUsername(e.target.value)} placeholder="admin" disabled={loading} />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">密码</label>
                <Input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} placeholder="请输入密码" disabled={loading} />
              </div>
              {error && <p className="rounded-md bg-red-50 p-2 text-sm text-red-600">{error}</p>}
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? '创建中...' : '创建管理员'}
              </Button>
              <div className="text-center text-sm">
                <Link href="/login" className="text-blue-600 hover:underline">返回登录</Link>
              </div>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
