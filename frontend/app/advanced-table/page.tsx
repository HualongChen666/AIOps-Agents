'use client'

import { useState, useRef, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';

interface TableRow {
  id: string;
  name: string;
  status: 'active' | 'inactive' | 'pending';
  cpu: number;
  memory: number;
  region: string;
  created: string;
}

export default function AdvancedTablePage() {
  const [data, setData] = useState<TableRow[]>([]);
  const [selectedRows, setSelectedRows] = useState<Set<string>>(new Set());
  const [frozenColumn, setFrozenColumn] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [virtualScrollIndex, setVirtualScrollIndex] = useState(0);
  const [batchAction, setBatchAction] = useState('');
  const tableContainerRef = useRef<HTMLDivElement>(null);

  // 从租户接口加载真实数据
  useEffect(() => {
    api
      .get('/api/v1/tenants')
      .then((res) => {
        const rows: TableRow[] = (res.data || []).map((t: any) => {
          const rawStatus = t.status?.toString().toLowerCase() || '';
          let status: 'active' | 'inactive' | 'pending';
          if (rawStatus === 'active') {
            status = 'active';
          } else if (rawStatus === 'suspended' || rawStatus === 'expired') {
            status = 'inactive';
          } else {
            status = 'pending';
          }
          return {
            id: t.id?.toString() || '',
            name: t.name?.toString() || '',
            status,
            cpu: Math.round(Number(t.usage?.cpu ?? 0)),
            memory: Math.round(Number(t.usage?.memory ?? 0)),
            region: t.plan?.toString() || t.contact?.toString() || 'unknown',
            created: t.created_at?.toString() || '',
          };
        });
        setData(rows);
      })
      .catch(() => setData([]));
  }, []);

  // 虚拟滚动处理
  useEffect(() => {
    const container = tableContainerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const scrollTop = container.scrollTop;
      const itemHeight = 50;
      const newIndex = Math.floor(scrollTop / itemHeight);
      setVirtualScrollIndex(newIndex);
    };

    container.addEventListener('scroll', handleScroll);
    return () => container.removeEventListener('scroll', handleScroll);
  }, []);

  // 过滤数据
  const filteredData = data.filter((row) =>
    row.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    row.id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // 虚拟滚动可见数据
  const visibleData = filteredData.slice(virtualScrollIndex, virtualScrollIndex + 20);

  // 行选择
  const toggleRowSelection = (id: string) => {
    const newSelection = new Set(selectedRows);
    if (newSelection.has(id)) {
      newSelection.delete(id);
    } else {
      newSelection.add(id);
    }
    setSelectedRows(newSelection);
  };

  // 全选
  const toggleSelectAll = () => {
    if (selectedRows.size === visibleData.length) {
      setSelectedRows(new Set());
    } else {
      setSelectedRows(new Set(visibleData.map((row) => row.id)));
    }
  };

  // 批量操作
  const handleBatchAction = () => {
    if (!batchAction) return;
    alert(`对 ${selectedRows.size} 行执行 ${batchAction} 操作`);
    setSelectedRows(new Set());
    setBatchAction('');
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'inactive':
        return 'bg-gray-100 text-gray-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const columns = [
    { key: 'id', label: 'ID', width: '100px' },
    { key: 'name', label: '名称', width: '150px' },
    { key: 'status', label: '状态', width: '100px' },
    { key: 'cpu', label: 'CPU %', width: '80px' },
    { key: 'memory', label: '内存 %', width: '100px' },
    { key: 'region', label: '区域', width: '120px' },
    { key: 'created', label: '创建时间', width: '180px' },
    { key: 'actions', label: '操作', width: '150px' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">高级数据表格</h1>
        <div className="flex items-center gap-2">
          <Badge variant="outline">{data.length} 条数据</Badge>
          <Badge variant="outline">{selectedRows.size} 已选择</Badge>
        </div>
      </div>

      {/* 功能概览 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">虚拟滚动</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-green-600">已启用</p>
            <p className="text-sm text-gray-500 mt-1">高性能渲染</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">列冻结</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{frozenColumn || '无'}</p>
            <p className="text-sm text-gray-500 mt-1">固定列位置</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">行选择</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{selectedRows.size}</p>
            <p className="text-sm text-gray-500 mt-1">已选行数</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">批量操作</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-blue-600">可用</p>
            <p className="text-sm text-gray-500 mt-1">多行处理</p>
          </CardContent>
        </Card>
      </div>

      {/* 表格控制 */}
      <Card>
        <CardHeader>
          <CardTitle>表格控制</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[200px]">
              <Input
                placeholder="搜索..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <Select value={frozenColumn || ''} onChange={(e) => setFrozenColumn(e.target.value || null)}>
              <option value="">无冻结列</option>
              {columns.map((col) => (
                <option key={col.key} value={col.key}>
                  冻结 {col.label}
                </option>
              ))}
            </Select>
          </div>

          {selectedRows.size > 0 && (
            <div className="flex items-center gap-4 p-4 bg-blue-50 rounded-lg">
              <span className="text-sm font-medium">已选择 {selectedRows.size} 行</span>
              <Select value={batchAction} onChange={(e) => setBatchAction(e.target.value)}>
                <option value="">选择操作</option>
                <option value="start">启动</option>
                <option value="stop">停止</option>
                <option value="restart">重启</option>
                <option value="delete">删除</option>
              </Select>
              <Button onClick={handleBatchAction} disabled={!batchAction}>
                执行
              </Button>
              <Button variant="outline" onClick={() => setSelectedRows(new Set())}>
                取消选择
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 高级表格 */}
      <Card>
        <CardHeader>
          <CardTitle>数据表格</CardTitle>
        </CardHeader>
        <CardContent>
          <div
            ref={tableContainerRef}
            className="border border-gray-200 rounded-lg overflow-auto"
            style={{ height: '500px' }}
          >
            <div style={{ minWidth: '1000px' }}>
              {/* 表头 */}
              <div className="flex bg-gray-50 border-b sticky top-0 z-10">
                <div className="p-3 w-12 flex items-center justify-center border-r">
                  <input
                    type="checkbox"
                    checked={selectedRows.size === visibleData.length && visibleData.length > 0}
                    onChange={toggleSelectAll}
                    className="w-4 h-4"
                  />
                </div>
                {columns.map((col) => (
                  <div
                    key={col.key}
                    className={`p-3 font-medium text-sm border-r ${frozenColumn === col.key ? 'sticky left-0 bg-gray-50 z-20' : ''
                      }`}
                    style={{ width: col.width }}
                  >
                    {col.label}
                  </div>
                ))}
              </div>

              {/* 表体 */}
              <div style={{ height: `${visibleData.length * 50}px` }}>
                {visibleData.map((row, index) => (
                  <div
                    key={row.id}
                    className={`flex border-b hover:bg-gray-50 ${selectedRows.has(row.id) ? 'bg-blue-50' : ''
                      }`}
                    style={{ height: '50px' }}
                  >
                    <div className="p-3 w-12 flex items-center justify-center border-r">
                      <input
                        type="checkbox"
                        checked={selectedRows.has(row.id)}
                        onChange={() => toggleRowSelection(row.id)}
                        className="w-4 h-4"
                      />
                    </div>
                    {columns.map((col) => (
                      <div
                        key={col.key}
                        className={`p-3 text-sm border-r flex items-center ${frozenColumn === col.key ? 'sticky left-0 bg-white z-10' : ''
                          }`}
                        style={{ width: col.width }}
                      >
                        {col.key === 'id' && (
                          <span className="font-mono">{row.id}</span>
                        )}
                        {col.key === 'name' && row.name}
                        {col.key === 'status' && (
                          <Badge className={getStatusColor(row.status)}>
                            {row.status}
                          </Badge>
                        )}
                        {col.key === 'cpu' && `${row.cpu}%`}
                        {col.key === 'memory' && `${row.memory}%`}
                        {col.key === 'region' && row.region}
                        {col.key === 'created' && new Date(row.created).toLocaleString()}
                        {col.key === 'actions' && (
                          <div className="flex gap-2">
                            <Button variant="outline" size="sm">
                              编辑
                            </Button>
                            <Button variant="outline" size="sm">
                              删除
                            </Button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          </div>
          <p className="text-sm text-gray-500 mt-2">
            显示 {virtualScrollIndex + 1}-{Math.min(virtualScrollIndex + 20, filteredData.length)} / {filteredData.length} 条数据
          </p>
        </CardContent>
      </Card>

      {/* 功能说明 */}
      <Card>
        <CardHeader>
          <CardTitle>功能说明</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">虚拟滚动</h4>
              <p className="text-sm text-gray-600">
                只渲染可见区域的行，大幅提升大数据量表格的性能。适合处理数千甚至数万条数据。
              </p>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">列冻结</h4>
              <p className="text-sm text-gray-600">
                固定重要列在左侧，滚动时保持可见。适合ID、名称等关键信息列。
              </p>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">行选择</h4>
              <p className="text-sm text-gray-600">
                支持单选和多选，配合批量操作功能。提供全选和取消全选功能。
              </p>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">批量操作</h4>
              <p className="text-sm text-gray-600">
                对选中的多行数据执行统一操作，如启动、停止、删除等，提高操作效率。
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 推荐库 */}
      <Card>
        <CardHeader>
          <CardTitle>推荐表格库</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">TanStack Table</h4>
              <p className="text-sm text-gray-600 mb-3">
                Headless UI表格库，提供完整的数据处理逻辑，完全自定义UI。
              </p>
              <Button variant="outline" size="sm" className="w-full">
                查看文档
              </Button>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">AG Grid</h4>
              <p className="text-sm text-gray-600 mb-3">
                企业级数据表格，功能丰富，性能优秀，支持大数据量。
              </p>
              <Button variant="outline" size="sm" className="w-full">
                查看文档
              </Button>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">React Table</h4>
              <p className="text-sm text-gray-600 mb-3">
                轻量级表格库，灵活的API，适合定制化需求。
              </p>
              <Button variant="outline" size="sm" className="w-full">
                查看文档
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
