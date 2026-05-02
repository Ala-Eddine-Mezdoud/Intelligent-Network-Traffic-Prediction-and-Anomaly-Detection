'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  BarChart3,
  TrendingUp,
  AlertTriangle,
  Bell,
  Activity,
  Database,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const navItems = [
  {
    href: '/',
    label: 'Dashboard',
    icon: Activity,
  },
  {
    href: '/traffic-prediction',
    label: 'Traffic Prediction',
    icon: TrendingUp,
  },
  {
    href: '/anomaly-detection',
    label: 'Anomaly Detection',
    icon: AlertTriangle,
  },
  {
    href: '/alerts',
    label: 'Alerts',
    icon: Bell,
  },
  {
    href: '/data-generation',
    label: 'Data Generation',
    icon: Database,
  },
];

export function SidebarNav() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r border-border bg-sidebar hidden md:block">
      <div className="flex h-16 items-center border-b border-sidebar-border px-6">
        <div className="flex items-center gap-2">
          <BarChart3 className="h-6 w-6 text-accent" />
          <span className="text-lg font-bold text-sidebar-foreground">NetGuard</span>
        </div>
      </div>
      <nav className="space-y-2 overflow-y-auto p-4 h-[calc(100vh-4rem)]">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-3 rounded-lg px-4 py-2.5 text-sm font-medium transition-colors whitespace-nowrap',
                isActive
                  ? 'bg-sidebar-primary text-sidebar-primary-foreground'
                  : 'text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground'
              )}
            >
              <Icon className="h-5 w-5 flex-shrink-0" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
