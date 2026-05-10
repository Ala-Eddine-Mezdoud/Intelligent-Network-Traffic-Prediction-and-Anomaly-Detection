'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  BarChart3,
  TrendingUp,
  AlertTriangle,
  Bell,
  Activity,
  Box,
  Database,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const navItems = [
  { href: '/',                   label: 'Dashboard',         icon: Activity     },
  { href: '/simulation',         label: 'Simulation Lab',    icon: Box          },
  { href: '/data-generation',    label: 'Data Generation',   icon: Database     },
  { href: '/traffic-prediction', label: 'Traffic Prediction',icon: TrendingUp   },
  { href: '/anomaly-detection',  label: 'Anomaly Detection', icon: AlertTriangle},
  { href: '/alerts',             label: 'Alerts',            icon: Bell         },
];

interface SidebarNavProps {
  open: boolean;
  onToggle: () => void;
}

export function SidebarNav({ open, onToggle }: SidebarNavProps) {
  const pathname = usePathname();

  return (
    <>
      {/* Sidebar panel */}
      <aside
        className={cn(
          'fixed left-0 top-0 z-40 h-screen w-64 border-r border-border bg-sidebar hidden md:flex flex-col transition-transform duration-300',
          open ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Header row */}
        <div className="flex h-16 items-center justify-between border-b border-sidebar-border px-6 flex-shrink-0">
          <div className="flex items-center gap-2">
            <BarChart3 className="h-6 w-6 text-accent" />
            <span className="text-lg font-bold text-sidebar-foreground">NetGuard</span>
          </div>
          {/* Collapse button */}
          <button
            onClick={onToggle}
            className="rounded-md p-1.5 text-sidebar-foreground hover:bg-sidebar-accent transition-colors"
            aria-label="Collapse sidebar"
          >
            <PanelLeftClose className="h-4 w-4" />
          </button>
        </div>

        {/* Nav links */}
        <nav className="space-y-2 overflow-y-auto p-4 flex-1">
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

      {/* Floating re-open button — only visible when sidebar is hidden */}
      {!open && (
        <button
          onClick={onToggle}
          className="fixed left-3 top-[18px] z-50 hidden md:flex items-center justify-center rounded-md p-1.5 bg-sidebar border border-border text-sidebar-foreground hover:bg-sidebar-accent transition-colors shadow-md"
          aria-label="Open sidebar"
        >
          <PanelLeftOpen className="h-4 w-4" />
        </button>
      )}
    </>
  );
}

