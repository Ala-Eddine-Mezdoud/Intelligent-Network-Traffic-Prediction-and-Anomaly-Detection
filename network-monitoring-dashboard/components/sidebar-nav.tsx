"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  AlertTriangle,
  Bell,
  Box,
  Database,
  TrendingUp,
  PanelLeftClose,
  PanelLeftOpen,
  ChevronRight,
  Moon,
  Sun,
  LifeBuoy,
  LogOut,
  UserCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";

const sections = [
  {
    key: "insights",
    title: "Insights",
    icon: Activity,
    items: [
      { href: "/", label: "Dashboard", icon: Activity },
      {
        href: "/traffic-prediction",
        label: "Traffic Prediction",
        icon: TrendingUp,
      },
      {
        href: "/anomaly-detection",
        label: "Anomaly Detection",
        icon: AlertTriangle,
      },
    ],
  },
  {
    key: "lab",
    title: "Lab & Data",
    icon: Box,
    items: [
      { href: "/simulation", label: "Simulation Lab", icon: Box },
      { href: "/data-generation", label: "Data Generation", icon: Database },
    ],
  },
  {
    key: "monitoring",
    title: "Monitoring",
    icon: Bell,
    items: [{ href: "/alerts", label: "Alerts", icon: Bell }],
  },
];

interface SidebarNavProps {
  open: boolean;
  compact: boolean;
  onToggle: () => void;
  onCompactToggle: () => void;
}

export function SidebarNav({
  open,
  compact,
  onToggle,
  onCompactToggle,
}: SidebarNavProps) {
  const pathname = usePathname();
  const [sectionsOpen, setSectionsOpen] = useState<Record<string, boolean>>({
    insights: true,
    lab: true,
    monitoring: true,
  });
  const [darkMode, setDarkMode] = useState(true);

  useEffect(() => {
    if (typeof document !== "undefined") {
      if (!document.documentElement.classList.contains("dark")) {
        document.documentElement.classList.add("dark");
      }
      setDarkMode(document.documentElement.classList.contains("dark"));
    }
  }, []);

  const toggleSection = (key: string) => {
    setSectionsOpen((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const toggleTheme = () => {
    if (typeof document !== "undefined") {
      document.documentElement.classList.toggle("dark");
      setDarkMode((prev) => !prev);
    }
  };

  return (
    <>
      <aside
        className={cn(
          "fixed left-0 top-0 z-40 h-screen overflow-hidden border-r border-slate-800 bg-white/5 backdrop-blur-xl text-slate-100 transition-all duration-300 ease-out hidden md:flex flex-col",
          open ? "translate-x-0" : "-translate-x-full",
          compact ? "w-20" : "w-72",
        )}
      >
        <div className="flex items-center justify-between border-b border-slate-800 px-4 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-sky-600 text-white">
              <UserCircle className="h-5 w-5 text-white" />
            </div>
            {!compact && (
              <div>
                <div className="text-sm font-semibold text-sky-100">
                  NetGuard
                </div>
                <div className="text-[11px] text-slate-300/70">
                  Network operations
                </div>
              </div>
            )}
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={onCompactToggle}
              className="rounded-lg p-2 text-slate-100 hover:bg-slate-900 hover:text-sky-200 transition-colors"
              aria-label={compact ? "Expand sidebar" : "Collapse sidebar"}
            >
              {compact ? (
                <PanelLeftOpen className="h-4 w-4 text-slate-100" />
              ) : (
                <PanelLeftClose className="h-4 w-4 text-slate-100" />
              )}
            </button>
            <button
              onClick={onToggle}
              className="rounded-lg p-2 text-slate-100 hover:bg-slate-900 hover:text-sky-200 transition-colors"
              aria-label="Toggle sidebar"
            >
              <ChevronRight
                className={cn(
                  "h-4 w-4 text-slate-100 transition-transform duration-300",
                  open ? "rotate-180" : "",
                )}
              />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-2 py-4">
          {sections.map((section) => {
            const SectionIcon = section.icon;
            const sectionExpanded = sectionsOpen[section.key];
            return (
              <div key={section.key} className="mb-4">
                <button
                  type="button"
                  onClick={() => toggleSection(section.key)}
                  className="flex w-full items-center gap-3 rounded-2xl px-3 py-2 text-left text-xs uppercase tracking-[0.18em] text-slate-300 transition-colors hover:bg-slate-900"
                >
                  <SectionIcon className="h-4 w-4 shrink-0 text-sky-400" />
                  {!compact && <span>{section.title}</span>}
                  <ChevronRight
                    className={cn(
                      "ml-auto h-4 w-4 text-slate-400 transition-transform duration-300",
                      sectionExpanded ? "rotate-90" : "",
                    )}
                  />
                </button>

                {sectionExpanded && (
                  <div className="mt-3 space-y-2">
                    {section.items.map((item) => {
                      const ItemIcon = item.icon;
                      const isActive = pathname === item.href;
                      return (
                        <Link
                          key={item.href}
                          href={item.href}
                          className={cn(
                            "group flex items-center gap-3 rounded-2xl px-3 py-2 text-sm font-medium transition-colors",
                            isActive
                              ? "bg-sky-700 text-slate-100 shadow-[0_0_0_1px_rgba(56,189,248,0.2)]"
                              : "text-slate-100 hover:bg-slate-900 hover:text-sky-200",
                          )}
                        >
                          <ItemIcon className="h-5 w-5 shrink-0 text-slate-100" />
                          {!compact && <span>{item.label}</span>}
                        </Link>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <div className="border-t border-slate-800 px-3 py-4">
          <div className="space-y-2">
            <button
              type="button"
              onClick={toggleTheme}
              className="flex w-full items-center gap-3 rounded-2xl px-3 py-2 text-sm font-medium text-slate-100 transition-colors hover:bg-slate-900"
            >
              {darkMode ? (
                <Moon className="h-4 w-4 text-slate-100" />
              ) : (
                <Sun className="h-4 w-4 text-slate-100" />
              )}
              {!compact && <span>{darkMode ? "Dark mode" : "Light mode"}</span>}
            </button>

            <Link
              href="/support"
              className="flex w-full items-center gap-3 rounded-2xl px-3 py-2 text-sm font-medium text-slate-100 transition-colors hover:bg-slate-900"
            >
              <LifeBuoy className="h-4 w-4 text-slate-100" />
              {!compact && <span>Support</span>}
            </Link>
          </div>
        </div>
      </aside>

      {!open && (
        <button
          onClick={onToggle}
          className="fixed left-3 top-4 z-50 hidden md:flex h-11 w-11 items-center justify-center rounded-full border border-slate-800 bg-white/5 backdrop-blur-md text-slate-100 shadow-lg transition hover:bg-white/10"
          aria-label="Open sidebar"
        >
          <PanelLeftOpen className="h-5 w-5 text-slate-100" />
        </button>
      )}
    </>
  );
}
