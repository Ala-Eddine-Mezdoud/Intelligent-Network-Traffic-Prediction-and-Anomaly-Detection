"use client";

import { useState } from "react";
import { SidebarNav } from "./sidebar-nav";
import { TopNavbar } from "./top-navbar";
import { AlertNotification } from "./alert-notification";
import { PageTransition } from "./motion/page-transition";

interface DashboardLayoutProps {
  children: React.ReactNode;
  navbarStatus?: "healthy" | "warning" | "critical";
  breadcrumbs?: Array<{ label: string; href?: string }>;
  onSearch?: (query: string) => void;
  onFilter?: () => void;
}

export function DashboardLayout({
  children,
  navbarStatus = "healthy",
  breadcrumbs = [{ label: "Dashboard" }],
  onSearch,
  onFilter,
}: DashboardLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [sidebarCompact, setSidebarCompact] = useState(false);

  return (
    <div className="min-h-screen bg-background">

      <SidebarNav
        open={sidebarOpen}
        compact={sidebarCompact}
        onToggle={() => setSidebarOpen((p) => !p)}
        onCompactToggle={() => setSidebarCompact((p) => !p)}
      />
      <TopNavbar
        status={navbarStatus}
        breadcrumbs={breadcrumbs}
        onSearch={onSearch}
        onFilter={onFilter}
        sidebarOpen={sidebarOpen}
        sidebarCompact={sidebarCompact}
      />
      <AlertNotification />
      <main
        className="relative z-10 mt-20 max-w-[1600px] space-y-8 p-4 transition-all duration-300 ease-out md:p-8"
        style={{
          marginLeft: sidebarOpen ? (sidebarCompact ? "5rem" : "18rem") : "0",
        }}
      >
        <PageTransition>{children}</PageTransition>
      </main>
    </div>
  );
}