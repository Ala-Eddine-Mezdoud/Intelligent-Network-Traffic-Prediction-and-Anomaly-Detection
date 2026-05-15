"use client";

import { CheckCircle, AlertCircle, Clock, Bell } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getAlertStats } from "@/lib/api";
import { cn } from "@/lib/utils";

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
  sidebarOpen = true,
  sidebarCompact = false,
}: TopNavbarProps) {
  const [alertCount, setAlertCount] = useState<number>(0);
  const router = useRouter();

  const getStatusStyles = () => {
    switch (status) {
      case "healthy":
        return {
          icon: <CheckCircle className="h-5 w-5 shrink-0 text-green-500" />,
          text: "System Healthy",
          textColor: "text-green-500",
          bg: "bg-green-500/10 border-green-500/30",
        };
      case "warning":
        return {
          icon: <AlertCircle className="h-5 w-5 shrink-0 text-orange-500" />,
          text: "Warning Active",
          textColor: "text-orange-500",
          bg: "bg-orange-500/10 border-orange-500/30",
        };
      case "critical":
        return {
          icon: <AlertCircle className="h-5 w-5 shrink-0 text-red-500" />,
          text: "Critical Issues",
          textColor: "text-red-500",
          bg: "bg-red-500/10 border-red-500/30",
        };
      default:
        return {
          icon: <CheckCircle className="h-5 w-5 shrink-0 text-green-500" />,
          text: "System Healthy",
          textColor: "text-green-500",
          bg: "bg-green-500/10 border-green-500/30",
        };
    }
  };

  const statusStyles = getStatusStyles();

  useEffect(() => {
    let mounted = true;
    async function fetchAlerts() {
      try {
        const stats = await getAlertStats();
        if (!mounted) return;
        setAlertCount(typeof stats.total === "number" ? stats.total : 0);
      } catch {
        /* ignore */
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
      className="fixed top-0 right-0 z-40 flex h-20 items-center justify-between border-b border-gray-200 bg-white px-4 shadow-sm transition-all duration-300 md:px-8"
      style={{
        left: sidebarOpen ? (sidebarCompact ? "5rem" : "18rem") : "0",
      }}
    >
      <nav className="hidden min-w-0 flex-1 items-center gap-2 text-sm md:flex">
        {breadcrumbs.map((crumb, index) => (
          <div key={index} className="flex items-center gap-2">
            {index > 0 && <span className="text-gray-400">/</span>}
            <span
              className={
                index === breadcrumbs.length - 1
                  ? "font-medium text-gray-900"
                  : "text-gray-500"
              }
            >
              {crumb.label}
            </span>
          </div>
        ))}
      </nav>

      <div className="flex shrink-0 items-center gap-3 md:gap-4">
        <div
          className={cn(
            "flex items-center gap-2 rounded-lg border px-3 py-1.5",
            statusStyles.bg,
          )}
        >
          {statusStyles.icon}
          <span
            className={cn(
              "hidden text-xs font-medium sm:inline md:text-sm",
              statusStyles.textColor,
            )}
          >
            {statusStyles.text}
          </span>
        </div>

        <div className="hidden items-center gap-2 text-sm text-gray-500 lg:flex">
          <Clock className="h-4 w-4" />
          <span>{new Date().toLocaleTimeString()}</span>
        </div>

        <Button
          variant="ghost"
          size="sm"
          className="relative text-gray-600 transition-all duration-200 ease-out hover:bg-[#f0f2f5] hover:text-gray-900 active:bg-[#e4e6eb]"
          onClick={() => router.push("/alerts")}
          aria-label="Open alerts"
        >
          <Bell className="h-4 w-4" />
          <Badge
            className={cn(
              "absolute -top-1 -right-1 flex h-5 min-w-[1.25rem] items-center justify-center px-1.5 p-0 text-xs text-white",
              alertCount > 0 ? "bg-red-500" : "bg-gray-400",
            )}
            aria-live="polite"
          >
            {alertCount}
          </Badge>
        </Button>
      </div>
    </header>
  );
}
