'use client'

import { useState, useEffect } from 'react';
import { useTheme } from '@/components/ThemeProvider';
import { AICopilot } from '@/components/ai/AICopilot';
import { useTenantStore } from '@/store/tenant';

export const Header = () => {
  const { theme, toggleTheme } = useTheme();
  const [showNotifications, setShowNotifications] = useState(false);
  const [showAICopilot, setShowAICopilot] = useState(false);
  const [showTenantSelector, setShowTenantSelector] = useState(false);
  
  const { currentTenant, tenants, setCurrentTenant } = useTenantStore();

  useEffect(() => {
    if (!currentTenant && tenants.length > 0) {
      setCurrentTenant(tenants[0]);
    }
  }, [currentTenant, tenants, setCurrentTenant]);

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-4">
        <div className="relative">
          <input
            type="text"
            placeholder="搜索..."
            className="w-64 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">🔍</span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {/* 租户选择器 */}
        <div className="relative">
          <button
            onClick={() => setShowTenantSelector(!showTenantSelector)}
            className="flex items-center gap-2 px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
          >
            <span className="text-sm font-medium">{currentTenant?.name || '选择租户'}</span>
            <span className="text-gray-400">▼</span>
          </button>
          
          {showTenantSelector && (
            <div className="absolute right-0 mt-2 w-64 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
              <div className="p-3 border-b border-gray-200">
                <h3 className="font-semibold text-sm">切换租户</h3>
              </div>
              <div className="max-h-64 overflow-y-auto">
                {tenants.map((tenant) => (
                  <button
                    key={tenant.id}
                    onClick={() => {
                      setCurrentTenant(tenant);
                      setShowTenantSelector(false);
                    }}
                    className={`w-full text-left px-4 py-3 hover:bg-gray-50 transition ${
                      currentTenant?.id === tenant.id ? 'bg-blue-50' : ''
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-sm">{tenant.name}</span>
                      {currentTenant?.id === tenant.id && (
                        <span className="text-blue-600">✓</span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        tenant.plan === 'enterprise' ? 'bg-purple-100 text-purple-800' :
                        tenant.plan === 'pro' ? 'bg-blue-100 text-blue-800' :
                        tenant.plan === 'basic' ? 'bg-green-100 text-green-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {tenant.plan}
                      </span>
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        tenant.status === 'active' ? 'bg-green-100 text-green-800' :
                        tenant.status === 'suspended' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {tenant.status === 'active' ? '活跃' : tenant.status === 'suspended' ? '暂停' : '过期'}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
              <div className="p-3 border-t border-gray-200">
                <button className="w-full text-sm text-blue-600 hover:text-blue-800 font-medium">
                  + 创建新租户
                </button>
              </div>
            </div>
          )}
        </div>

        {/* AI Copilot 按钮 */}
        <button 
          onClick={() => setShowAICopilot(true)}
          className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:opacity-90 transition"
        >
          <span>🤖</span>
          <span className="font-medium">AI Copilot</span>
        </button>

        {/* 通知 */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="p-2 hover:bg-gray-100 rounded-lg transition"
          >
            <span className="text-xl">🔔</span>
            <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
              3
            </span>
          </button>
          
          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
              <div className="p-4 border-b border-gray-200">
                <h3 className="font-semibold">通知</h3>
              </div>
              <div className="max-h-64 overflow-y-auto">
                <div className="p-3 hover:bg-gray-50 border-b border-gray-100">
                  <p className="text-sm font-medium">新告警: CPU使用率过高</p>
                  <p className="text-xs text-gray-500">2分钟前</p>
                </div>
                <div className="p-3 hover:bg-gray-50 border-b border-gray-100">
                  <p className="text-sm font-medium">修复任务已完成</p>
                  <p className="text-xs text-gray-500">5分钟前</p>
                </div>
                <div className="p-3 hover:bg-gray-50">
                  <p className="text-sm font-medium">系统健康度更新</p>
                  <p className="text-xs text-gray-500">10分钟前</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 主题切换 */}
        <button
          onClick={toggleTheme}
          className="p-2 hover:bg-gray-100 rounded-lg transition"
          title="切换主题"
        >
          {theme === 'light' ? '🌙' : '☀️'}
        </button>

        {/* 用户菜单 */}
        <div className="flex items-center gap-3 pl-4 border-l border-gray-200">
          <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white font-bold">
            U
          </div>
          <div className="hidden md:block">
            <p className="text-sm font-medium">用户</p>
            <p className="text-xs text-gray-500">管理员</p>
          </div>
        </div>
      </div>

      {/* AI Copilot 弹窗 */}
      {showAICopilot && <AICopilot />}
    </header>
  );
};
