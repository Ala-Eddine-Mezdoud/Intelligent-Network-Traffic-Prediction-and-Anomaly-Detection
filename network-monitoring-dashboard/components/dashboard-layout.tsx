'use client';

import { SidebarNav } from './sidebar-nav';
import { TopNavbar } from './top-navbar';

interface DashboardLayoutProps {
  children: React.ReactNode;
  navbarStatus?: 'healthy' | 'warning';
}

export function DashboardLayout({
  children,
  navbarStatus = 'healthy',
}: DashboardLayoutProps) {
  return (
    <div className="min-h-screen bg-background">
      <SidebarNav />
      <TopNavbar status={navbarStatus} />
      <main className="md:ml-64 mt-16 p-4 md:p-8 space-y-8">
        {children}
      </main>
    </div>
  );
}
