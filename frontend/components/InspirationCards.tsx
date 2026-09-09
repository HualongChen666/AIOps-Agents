'use client';

import { Card, CardContent } from '@/components/ui/card';
import { Server, Database, Shield, Activity, TrendingUp, Clock } from 'lucide-react';

interface InspirationCard {
  id: string;
  title: string;
  description: string;
  icon: React.ElementType;
  category: string;
}

export function InspirationCards() {
  const cards: InspirationCard[] = [
    {
      id: 'capacity',
      title: '容量巡检',
      description: '一键发起容量水位巡检，评估资源使用情况',
      icon: Server,
      category: '容量管理',
    },
    {
      id: 'cost',
      title: '成本健康',
      description: '分析资源成本，提供优化建议',
      icon: TrendingUp,
      category: '成本优化',
    },
    {
      id: 'security',
      title: '安全合规',
      description: '检查安全配置，识别合规风险',
      icon: Shield,
      category: '安全',
    },
    {
      id: 'performance',
      title: '性能分析',
      description: '分析系统性能，识别瓶颈',
      icon: Activity,
      category: '性能',
    },
    {
      id: 'database',
      title: '数据库巡检',
      description: '检查数据库健康状态和性能',
      icon: Database,
      category: '数据库',
    },
    {
      id: 'sla',
      title: 'SLA监控',
      description: '监控服务级别协议，保障服务质量',
      icon: Clock,
      category: 'SRE',
    },
  ];

  const handleCardClick = (card: InspirationCard) => {
    console.log('触发灵感卡片:', card.id);
    // 这里可以添加实际的触发逻辑
  };

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">灵感卡片</h2>
        <p className="text-sm text-gray-500 mt-1">选择预设巡检主题，一键发起智能分析</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {cards.map((card) => (
          <Card
            key={card.id}
            className="cursor-pointer hover:shadow-lg transition-all hover:scale-105"
            onClick={() => handleCardClick(card)}
          >
            <CardContent className="p-6">
              <div className="flex items-start gap-4">
                <div className="p-3 bg-blue-50 rounded-lg">
                  <card.icon className="h-6 w-6 text-blue-600" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-900">{card.title}</h3>
                  <p className="text-sm text-gray-500 mt-1">{card.description}</p>
                  <div className="mt-2">
                    <span className="inline-block px-2 py-1 text-xs font-medium bg-gray-100 text-gray-600 rounded">
                      {card.category}
                    </span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
