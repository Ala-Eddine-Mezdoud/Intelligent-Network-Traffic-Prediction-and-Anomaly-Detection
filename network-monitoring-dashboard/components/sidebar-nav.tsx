"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Bell,
  ChevronRight,
  Database,
  FlaskConical,
  LayoutDashboard,
  LifeBuoy,
  Network,
  PanelLeftClose,
  PanelLeftOpen,
  Radar,
  ShieldCheck,
  TrendingUp,
  Workflow,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  navIconButton,
  navItem,
  navItemActive,
  navItemIcon,
  navItemIconActive,
  navItemIconIdle,
  navItemIdle,
  navSectionButton,
} from "@/lib/ui-theme";

type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  description?: string;
};

type NavSection = {
  key: string;
  title: string;
  /** Category icon — always different from child item icons */
  icon: LucideIcon;
  items: NavItem[];
};

const sections: NavSection[] = [
  {
    key: "insights",
    title: "Insights",
    icon: BarChart3,
    items: [
      {
        href: "/",
        label: "Dashboard",
        icon: LayoutDashboard,
        description: "Network overview",
      },
      {
        href: "/traffic-prediction",
        label: "Traffic Prediction",
        icon: TrendingUp,
        description: "Forecast & trends",
      },
      {
        href: "/anomaly-detection",
        label: "Anomaly Detection",
        icon: Radar,
        description: "Threat analysis",
      },
    ],
  },
  {
    key: "lab",
    title: "Lab & Data",
    icon: FlaskConical,
    items: [
      {
        href: "/simulation",
        label: "Simulation Lab",
        icon: Workflow,
        description: "Mininet topology",
      },
      {
        href: "/data-generation",
        label: "Data Generation",
        icon: Database,
        description: "GNN datasets",
      },
    ],
  },
  {
    key: "monitoring",
    title: "Monitoring",
    icon: ShieldCheck,
    items: [
      {
        href: "/alerts",
        label: "Alerts",
        icon: Bell,
        description: "Incidents & notifications",
      },
    ],
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

  const toggleSection = (key: string) => {
    setSectionsOpen((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <>
      <aside
        className={cn(
          "fixed left-0 top-0 z-40 hidden h-screen flex-col overflow-hidden border-r border-gray-200 bg-white text-gray-900 transition-all duration-300 ease-out md:flex",
          open ? "translate-x-0" : "-translate-x-full",
          compact ? "w-20" : "w-72",
        )}
      >
        <div className="flex items-center justify-between border-b border-gray-200 px-4 py-5">
          <div className="flex items-center gap-3">
            <div
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-gray-200 bg-gray-50 text-gray-900"
              aria-hidden
            >
              <Network className="h-5 w-5 stroke-[1.75]" />
            </div>
            {!compact && (
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-gray-900">
                  NetGuard
                </p>
                <p className="text-[11px] text-gray-500">Network operations</p>
              </div>
            )}
          </div>
          <button
            type="button"
            onClick={onCompactToggle}
            className={navIconButton}
            aria-label={compact ? "Expand sidebar" : "Collapse sidebar"}
          >
            {compact ? (
              <PanelLeftOpen className="h-4 w-4" />
            ) : (
              <PanelLeftClose className="h-4 w-4" />
            )}
          </button>
        </div>

        <nav
          className="flex-1 overflow-y-auto px-3 py-4"
          aria-label="Main navigation"
        >
          {sections.map((section) => {
            const SectionIcon = section.icon;
            const sectionExpanded = sectionsOpen[section.key];
            return (
              <div key={section.key} className="mb-4">
                <button
                  type="button"
                  onClick={() => toggleSection(section.key)}
                  className={cn(navSectionButton, compact && "justify-center px-2")}
                  aria-expanded={sectionExpanded}
                >
                  <SectionIcon
                    className="h-4 w-4 shrink-0 stroke-[1.75] text-gray-400 transition-colors duration-200 group-hover:text-gray-600"
                    aria-hidden
                  />
                  {!compact && (
                    <span className="font-medium tracking-tight">
                      {section.title}
                    </span>
                  )}
                  {!compact && (
                    <ChevronRight
                      className={cn(
                        "ml-auto h-4 w-4 text-gray-400 transition-transform duration-300",
                        sectionExpanded && "rotate-90",
                      )}
                      aria-hidden
                    />
                  )}
                </button>

                {sectionExpanded && (
                  <ul className="mt-2 space-y-0.5" role="list">
                    {section.items.map((item) => {
                      const ItemIcon = item.icon;
                      const isActive = pathname === item.href;
                      return (
                        <li key={item.href}>
                          <Link
                            href={item.href}
                            title={compact ? item.label : item.description}
                            className={cn(
                              navItem,
                              isActive ? navItemActive : navItemIdle,
                              compact && "justify-center px-2",
                            )}
                            aria-current={isActive ? "page" : undefined}
                          >
                            <ItemIcon
                              className={cn(
                                navItemIcon,
                                "stroke-[1.75]",
                                isActive
                                  ? navItemIconActive
                                  : navItemIconIdle,
                              )}
                              aria-hidden
                            />
                            {!compact && (
                              <span className="truncate">{item.label}</span>
                            )}
                          </Link>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            );
          })}
        </nav>

        <div className="border-t border-gray-200 px-3 py-4">
          <Link
            href="/support"
            title={compact ? "Support" : "Help & documentation"}
            className={cn(navItem, navItemIdle, compact && "justify-center px-2")}
          >
            <LifeBuoy
              className={cn(
                navItemIcon,
                navItemIconIdle,
                "stroke-[1.75]",
              )}
              aria-hidden
            />
            {!compact && <span>Support</span>}
          </Link>
        </div>
      </aside>

      {!open && (
        <button
          type="button"
          onClick={onToggle}
          className="fixed left-3 top-4 z-50 hidden h-11 w-11 items-center justify-center rounded-full border border-gray-200 bg-white text-gray-700 shadow-sm transition-all duration-200 ease-out hover:bg-[#f0f2f5] hover:text-gray-900 active:bg-[#e4e6eb] md:flex"
          aria-label="Open sidebar"
        >
          <PanelLeftOpen className="h-5 w-5" />
        </button>
      )}
    </>
  );
}
