'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import api from '@/lib/api';

interface Certificate {
  id: string;
  domain: string;
  issuer: string;
  subject: string;
  validFrom: string;
  validTo: string;
  status: 'valid' | 'expired' | 'revoked' | 'expiring_soon';
  algorithm: string;
  keySize: number;
  autoRenew: boolean;
}

interface SSLConfig {
  id: string;
  domain: string;
  protocol: 'TLSv1.2' | 'TLSv1.3';
  cipherSuites: string[];
  hstsEnabled: boolean;
  hstsMaxAge: number;
  ocspStapling: boolean;
  certificateId: string;
  status: 'active' | 'inactive';
}

interface SecurityHeader {
  id: string;
  domain: string;
  header: string;
  value: string;
  enabled: boolean;
  description: string;
}

export default function HttpsPage() {
  const { isLoading, error, setLoading, setError } = useLoadingState(false);
  const { success, error: showError } = useToast();
  const [certificates, setCertificates] = useState<Certificate[]>([]);
  const [configs, setConfigs] = useState<SSLConfig[]>([]);
  const [headers, setHeaders] = useState<SecurityHeader[]>([]);
  const [activeTab, setActiveTab] = useState<'certificates' | 'configs' | 'headers'>('certificates');

  const loadHttpsData = async () => {
    setLoading(true);
    try {
      const [certsRes, configsRes, headersRes] = await Promise.all([
        api.get('/api/v1/security/https/certificates'),
        api.get('/api/v1/security/https/configs'),
        api.get('/api/v1/security/https/headers'),
      ]);

      const certsData = certsRes.data?.certificates || [];
      const configsData = configsRes.data?.configs || [];
      const headersData = headersRes.data?.headers || [];

      setCertificates(certsData);
      setConfigs(configsData);
      setHeaders(headersData);
      setLoading(false);
    } catch (err) {
      setError(err as Error);
      setLoading(false);
    }
  };

  const handleRenewCertificate = async (certId: string) => {
    try {
      await api.post(`/api/v1/security/https/certificates/${certId}/renew`);
      success('证书续期请求已提交');
      loadHttpsData();
    } catch (err) {
      showError('证书续期失败');
    }
  };

  const handleToggleAutoRenew = async (certId: string, autoRenew: boolean) => {
    try {
      await api.patch(`/api/v1/security/https/certificates/${certId}`, { autoRenew });
      success('自动续期设置已更新');
      loadHttpsData();
    } catch (err) {
      showError('设置更新失败');
    }
  };

  const handleToggleConfig = async (configId: string, status: string) => {
    try {
      await api.patch(`/api/v1/security/https/configs/${configId}`, { status });
      success('配置状态更新成功');
      loadHttpsData();
    } catch (err) {
      showError('配置状态更新失败');
    }
  };

  const handleToggleHeader = async (headerId: string, enabled: boolean) => {
    try {
      await api.patch(`/api/v1/security/https/headers/${headerId}`, { enabled });
      success('安全头状态更新成功');
      loadHttpsData();
    } catch (err) {
      showError('安全头状态更新失败');
    }
  };

  useEffect(() => {
    loadHttpsData();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-600 dark:text-gray-400">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-red-600 dark:text-red-400">Error: {error.message}</div>
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'valid':
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'expired':
      case 'revoked':
      case 'inactive':
        return 'bg-red-100 text-red-800';
      case 'expiring_soon':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const tabs = [
    { key: 'certificates' as const, label: 'SSL证书' },
    { key: 'configs' as const, label: 'SSL配置' },
    { key: 'headers' as const, label: '安全头' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">HTTPS配置</h1>
        <Button onClick={loadHttpsData}>刷新数据</Button>
      </div>

      {/* 标签页 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-2">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-4 py-2 rounded-lg font-medium transition ${activeTab === tab.key
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* SSL证书 */}
      {activeTab === 'certificates' && (
        <Card>
          <CardHeader>
            <CardTitle>SSL证书</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>域名</TableHead>
                  <TableHead>颁发者</TableHead>
                  <TableHead>主题</TableHead>
                  <TableHead>算法</TableHead>
                  <TableHead>密钥大小</TableHead>
                  <TableHead>生效日期</TableHead>
                  <TableHead>过期日期</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>自动续期</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {certificates.length > 0 ? certificates.map((cert) => (
                  <TableRow key={cert.id}>
                    <TableCell className="font-medium">{cert.domain}</TableCell>
                    <TableCell>{cert.issuer}</TableCell>
                    <TableCell className="text-sm max-w-xs truncate">{cert.subject}</TableCell>
                    <TableCell>{cert.algorithm}</TableCell>
                    <TableCell>{cert.keySize} bits</TableCell>
                    <TableCell>{new Date(cert.validFrom).toLocaleDateString()}</TableCell>
                    <TableCell>{new Date(cert.validTo).toLocaleDateString()}</TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(cert.status)}>{cert.status}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={cert.autoRenew ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                        {cert.autoRenew ? '是' : '否'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleRenewCertificate(cert.id)}
                        >
                          续期
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleToggleAutoRenew(cert.id, !cert.autoRenew)}
                        >
                          {cert.autoRenew ? '关闭自动' : '开启自动'}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={10} className="text-center text-gray-500">
                      No SSL certificates found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* SSL配置 */}
      {activeTab === 'configs' && (
        <Card>
          <CardHeader>
            <CardTitle>SSL配置</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>域名</TableHead>
                  <TableHead>协议</TableHead>
                  <TableHead>密码套件</TableHead>
                  <TableHead>HSTS</TableHead>
                  <TableHead>HSTS Max Age</TableHead>
                  <TableHead>OCSP Stapling</TableHead>
                  <TableHead>证书ID</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {configs.length > 0 ? configs.map((config) => (
                  <TableRow key={config.id}>
                    <TableCell className="font-medium">{config.domain}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{config.protocol}</Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {config.cipherSuites.slice(0, 2).map((cipher, idx) => (
                          <Badge key={idx} variant="outline" className="text-xs">{cipher}</Badge>
                        ))}
                        {config.cipherSuites.length > 2 && (
                          <Badge variant="outline" className="text-xs">+{config.cipherSuites.length - 2}</Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge className={config.hstsEnabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                        {config.hstsEnabled ? '是' : '否'}
                      </Badge>
                    </TableCell>
                    <TableCell>{config.hstsMaxAge} 天</TableCell>
                    <TableCell>
                      <Badge className={config.ocspStapling ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                        {config.ocspStapling ? '是' : '否'}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono text-sm">{config.certificateId}</TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(config.status)}>{config.status}</Badge>
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleToggleConfig(config.id, config.status === 'active' ? 'inactive' : 'active')}
                      >
                        {config.status === 'active' ? '禁用' : '启用'}
                      </Button>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center text-gray-500">
                      No SSL configurations found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 安全头 */}
      {activeTab === 'headers' && (
        <Card>
          <CardHeader>
            <CardTitle>安全头</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>域名</TableHead>
                  <TableHead>头名称</TableHead>
                  <TableHead>值</TableHead>
                  <TableHead>描述</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {headers.length > 0 ? headers.map((header) => (
                  <TableRow key={header.id}>
                    <TableCell className="font-medium">{header.domain}</TableCell>
                    <TableCell className="font-mono text-sm">{header.header}</TableCell>
                    <TableCell className="font-mono text-sm max-w-xs truncate">{header.value}</TableCell>
                    <TableCell className="text-sm max-w-xs truncate">{header.description}</TableCell>
                    <TableCell>
                      <Badge className={header.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                        {header.enabled ? '启用' : '禁用'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleToggleHeader(header.id, !header.enabled)}
                      >
                        {header.enabled ? '禁用' : '启用'}
                      </Button>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-gray-500">
                      No security headers found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
