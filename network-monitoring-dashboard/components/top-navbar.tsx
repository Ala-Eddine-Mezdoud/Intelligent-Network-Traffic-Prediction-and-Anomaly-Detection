"use client";

import { CheckCircle, AlertCircle, Clock, Bell } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getAlertStats } from "@/lib/api";

interface TopNavbarProps {
  status?: "healthy" | "warning" | "critical";
  breadcrumbs?: Array<{ label: string; href?: string }>;
  onSearch?: (query: string) => void;
  onFilter?: () => void;
  sidebarOpen?: boolean;
  sidebarCompact?: boolean;
}

export function TopNavbar({
  status = "healthy",
  breadcrumbs = [{ label: "Network Traffic Monitor" }],
  onSearch,
  onFilter,
  sidebarOpen = true,
  sidebarCompact = false,
}: TopNavbarProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [alertCount, setAlertCount] = useState<number>(0);
  const router = useRouter();

  const getStatusStyles = () => {
    switch (status) {
      case "healthy":
        return {
          icon: (
            <CheckCircle className="h-5 w-5 text-health-green shrink-0 animate-pulse" />
          ),
          text: "System Healthy",
          textColor: "text-health-green",
          bg: "bg-health-green-bg border-health-green-border",
        };
      case "warning":
        return {
          icon: (
            <AlertCircle className="h-5 w-5 text-health-orange shrink-0 animate-pulse" />
          ),
          text: "Warning Active",
          textColor: "text-health-orange",
          bg: "bg-health-orange-bg border-health-orange-border",
        };
      case "critical":
        return {
          icon: (
            <AlertCircle className="h-5 w-5 text-health-red shrink-0 animate-pulse" />
          ),
          text: "Critical Issues",
          textColor: "text-health-red",
          bg: "bg-health-red-bg border-health-red-border",
        };
      default:
        return {
          icon: <CheckCircle className="h-5 w-5 text-health-green shrink-0" />,
          text: "System Healthy",
          textColor: "text-health-green",
          bg: "bg-health-green-bg border-health-green-border",
        };
    }
  };

  const statusStyles = getStatusStyles();

  // Poll alert stats periodically to keep notification badge in sync
  useEffect(() => {
    let mounted = true;
    async function fetchAlerts() {
      try {
        const stats = await getAlertStats();
        if (!mounted) return;
        setAlertCount(typeof stats.total === "number" ? stats.total : 0);
      } catch (e) {
        // ignore errors silently
      }
    }

    fetchAlerts();
    const id = setInterval(fetchAlerts, 15000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  return (
    <header 
      className="fixed top-0 left-0 right-0 h-16 border-b border-border bg-white/5 backdrop-blur-xl px-4 md:px-8 flex items-center justify-between z-40 shadow-lg shadow-slate-950/20 transition-all duration-300"
      style={{
        left: sidebarOpen ? (sidebarCompact ? "5rem" : "18rem") : "0",
      }}
    >
      {/* Left Section - Breadcrumbs and Title */}
      <div className="flex-1 min-w-0 flex items-center gap-4">
        {/* Breadcrumbs */}
        <nav className="hidden md:flex items-center gap-2 text-sm">
          {breadcrumbs.map((crumb, index) => (
            <div key={index} className="flex items-center gap-2">
              {index > 0 && <span className="text-muted-foreground">/</span>}
              <span
                className={
                  index === breadcrumbs.length - 1
                    ? "text-foreground font-medium"
                    : "text-muted-foreground hover:text-foreground cursor-pointer"
                }
              >
                {crumb.label}
              </span>
            </div>
          ))}
        </nav>
      </div>

      {/* Right Section - Status, Time, Actions */}
      <div className="flex items-center gap-3 md:gap-4 shrink-0">
        {/* System Status */}
        <div
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border ${statusStyles.bg} transition-all duration-300`}
        >
          {statusStyles.icon}
          <span
            className={`text-xs md:text-sm font-medium ${statusStyles.textColor} hidden sm:inline`}
          >
            {statusStyles.text}
          </span>
        </div>

        {/* Current Time */}
        <div className="hidden lg:flex items-center gap-2 text-sm text-muted-foreground">
          <Clock className="h-4 w-4" />
          <span>{new Date().toLocaleTimeString()}</span>
        </div>

        {/* Notifications */}
        <Button
          variant="ghost"
          size="sm"
          className="relative hover:bg-muted/50"
          onClick={() => router.push("/alerts")}
          aria-label="Open alerts"
        >
          <Bell className="h-4 w-4" />
          <Badge
            className={`absolute -top-1 -right-1 h-5 min-w-[1.25rem] flex items-center justify-center px-1.5 p-0 text-xs text-white ${
              alertCount > 0 ? "bg-health-red" : "bg-zinc-700/40"
            }`}
            aria-live="polite"
          >
            {alertCount}
          </Badge>
        </Button>
      </div>
    </header>
  );
}
