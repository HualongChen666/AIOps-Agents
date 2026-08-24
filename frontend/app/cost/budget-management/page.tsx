'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import api from '@/lib/api';

interface Budget {
  id: string;
  name: string;
  service: string;
  amount: number;
  spent: number;
  remaining: number;
  period: string;
  status: 'on_track' | 'warning' | 'exceeded';
  alerts_enabled: boolean;
}

export default function BudgetManagementPage() {
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newBudget, setNewBudget] = useState({
    name: '',
    service: '',
    amount: 0,
    period: 'monthly'
  });

  useEffect(() => {
    fetchBudgets();
  }, []);

  const fetchBudgets = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/cost/budget-management');
      setBudgets(res.data.budgets || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载预算失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    try {
      await api.post('/api/cost/budget-management', newBudget);
      setNewBudget({ name: '', service: '', amount: 0, period: 'monthly' });
      fetchBudgets();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '创建预算失败');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'on_track': return 'bg-green-100 text-green-800';
      case 'warning': return 'bg-yellow-100 text-yellow-800';
      case 'exceeded': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchBudgets} className="mt-2">重试</Button></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">预算管理</h1>
        <Button onClick={fetchBudgets}>刷新</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>创建新预算</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              placeholder="预算名称"
              value={newBudget.name}
              onChange={(e) => setNewBudget({ ...newBudget, name: e.target.value })}
            />
            <Input
              placeholder="服务"
              value={newBudget.service}
              onChange={(e) => setNewBudget({ ...newBudget, service: e.target.value })}
            />
            <Input
              type="number"
              placeholder="金额"
              value={newBudget.amount}
              onChange={(e) => setNewBudget({ ...newBudget, amount: parseFloat(e.target.value) || 0 })}
            />
            <Input
              placeholder="周期 (如: monthly)"
              value={newBudget.period}
              onChange={(e) => setNewBudget({ ...newBudget, period: e.target.value })}
            />
          </div>
          <Button onClick={handleCreate} className="mt-4">创建</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>预算列表</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>名称</TableHead>
                <TableHead>服务</TableHead>
                <TableHead>预算</TableHead>
                <TableHead>已使用</TableHead>
                <TableHead>剩余</TableHead>
                <TableHead>周期</TableHead>
                <TableHead>状态</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {budgets.map((budget) => (
                <TableRow key={budget.id}>
                  <TableCell className="font-medium">{budget.name}</TableCell>
                  <TableCell>{budget.service}</TableCell>
                  <TableCell>${budget.amount.toFixed(2)}</TableCell>
                  <TableCell>${budget.spent.toFixed(2)}</TableCell>
                  <TableCell className={budget.remaining < 0 ? 'text-red-600 font-semibold' : ''}>
                    ${budget.remaining.toFixed(2)}
                  </TableCell>
                  <TableCell>{budget.period}</TableCell>
                  <TableCell>
                    <Badge className={getStatusColor(budget.status)}>
                      {budget.status === 'on_track' ? '正常' : budget.status === 'warning' ? '警告' : '超支'}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
