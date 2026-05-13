"use client";

import { useState } from "react";
import { SidebarNav } from "./sidebar-nav";
import { TopNavbar } from "./top-navbar";
import { AlertNotification } from "./alert-notification";

interface DashboardLayoutProps {
  children: React.ReactNode;
  navbarStatus?: "healthy" | "warning";
}

export function DashboardLayout({
  children,
  navbarStatus = "healthy",
}: DashboardLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="min-h-screen bg-background">
      <SidebarNav
        open={sidebarOpen}
        onToggle={() => setSidebarOpen((p) => !p)}
      />
      <TopNavbar status={navbarStatus} />
      <AlertNotification />
      <main
        className="mt-16 p-4 md:p-6 space-y-8 transition-all duration-300"
        style={{ marginLeft: sidebarOpen ? "16rem" : "0" }}
      >
        {children}
      </main>
    </div>
  );
}
