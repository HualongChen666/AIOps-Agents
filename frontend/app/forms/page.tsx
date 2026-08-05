'use client'

import { useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';

interface ChangeRequestForm {
  title: string;
  description: string;
  requester: string;
  approver: string;
  risk_level: 'low' | 'medium' | 'high';
  schedule: string;
  affected_services: string;
  implementation_plan: string;
  rollback_plan: string;
}

const INITIAL_FORM: ChangeRequestForm = {
  title: '',
  description: '',
  requester: '',
  approver: '',
  risk_level: 'low',
  schedule: '',
  affected_services: '',
  implementation_plan: '',
  rollback_plan: '',
};

export default function FormsPage() {
  const [form, setForm] = useState<ChangeRequestForm>(INITIAL_FORM);
  const [submitting, setSubmitting] = useState(false);

  const updateField = <K extends keyof ChangeRequestForm>(
    field: K,
    value: ChangeRequestForm[K]
  ) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);

    const payload = {
      title: form.title,
      description: form.description,
      requester: form.requester,
      approver: form.approver,
      risk_level: form.risk_level,
      schedule: form.schedule,
      affected_services: form.affected_services
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean),
      implementation_plan: form.implementation_plan,
      rollback_plan: form.rollback_plan,
    };

    try {
      await api.post('/api/v1/change-management/requests', payload);
      alert('变更请求创建成功');
      setForm(INITIAL_FORM);
    } catch {
      // API interceptor already displays the error via toast
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">创建变更请求</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>变更请求信息</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                标题
              </label>
              <Input
                required
                value={form.title}
                onChange={(e) => updateField('title', e.target.value)}
                placeholder="请输入变更标题"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                描述
              </label>
              <textarea
                value={form.description}
                onChange={(e) => updateField('description', e.target.value)}
                placeholder="请输入变更描述"
                className="min-h-[80px] w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  申请人
                </label>
                <Input
                  required
                  value={form.requester}
                  onChange={(e) => updateField('requester', e.target.value)}
                  placeholder="请输入申请人"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  审批人
                </label>
                <Input
                  value={form.approver}
                  onChange={(e) => updateField('approver', e.target.value)}
                  placeholder="请输入审批人"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  风险等级
                </label>
                <Select
                  value={form.risk_level}
                  onChange={(e) =>
                    updateField('risk_level', e.target.value as ChangeRequestForm['risk_level'])
                  }
                >
                  <option value="low">低</option>
                  <option value="medium">中</option>
                  <option value="high">高</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  计划执行时间
                </label>
                <Input
                  type="datetime-local"
                  value={form.schedule}
                  onChange={(e) => updateField('schedule', e.target.value)}
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                受影响服务
              </label>
              <Input
                value={form.affected_services}
                onChange={(e) => updateField('affected_services', e.target.value)}
                placeholder="service1, service2, service3"
              />
              <p className="mt-1 text-xs text-gray-500">
                多个服务请用英文逗号分隔
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                实施方案
              </label>
              <textarea
                value={form.implementation_plan}
                onChange={(e) => updateField('implementation_plan', e.target.value)}
                placeholder="请输入实施方案"
                className="min-h-[80px] w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                回滚方案
              </label>
              <textarea
                value={form.rollback_plan}
                onChange={(e) => updateField('rollback_plan', e.target.value)}
                placeholder="请输入回滚方案"
                className="min-h-[80px] w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
              />
            </div>

            <div className="flex justify-end">
              <Button type="submit" disabled={submitting}>
                {submitting ? '创建中...' : '创建变更请求'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
