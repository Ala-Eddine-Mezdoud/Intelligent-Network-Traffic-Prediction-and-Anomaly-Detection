"use client";

import { motion } from "framer-motion";
import {
  Search,
  RefreshCw,
  Maximize2,
  Focus,
  Filter,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { springSnappy } from "@/lib/motion";

export type HealthFilter = "all" | "healthy" | "warning" | "critical";

interface TopologyControlsProps {
  onSearch: (q: string) => void;
  onResetZoom: () => void;
  onRefresh: () => void;
  focusMode: boolean;
  onFocusModeChange: (v: boolean) => void;
  healthFilter: HealthFilter;
  onHealthFilterChange: (v: HealthFilter) => void;
}

const HEALTH_FILTERS: { id: HealthFilter; label: string; dot: string }[] = [
  { id: "all", label: "All", dot: "bg-muted-foreground" },
  { id: "healthy", label: "Healthy", dot: "bg-green-500" },
  { id: "warning", label: "Warning", dot: "bg-orange-500" },
  { id: "critical", label: "Critical", dot: "bg-red-500" },
];

export function TopologyControls({
  onSearch,
  onResetZoom,
  onRefresh,
  focusMode,
  onFocusModeChange,
  healthFilter,
  onHealthFilterChange,
}: TopologyControlsProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springSnappy}
      className="absolute left-4 top-4 z-40 flex max-w-[calc(100%-2rem)] flex-col gap-2"
    >
      <div className="group relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground transition-colors group-focus-within:text-muted-foreground" />
        <Input
          placeholder="Search hostname or IP…"
          className="h-10 w-72 rounded-xl border-border bg-card/95 pl-10 text-xs text-foreground shadow-sm backdrop-blur-sm transition-shadow focus-visible:ring-gray-300 focus-visible:shadow-md"
          onChange={(e) => onSearch(e.target.value)}
        />
      </div>

      <motion.div
        className="flex flex-wrap items-center gap-2"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.05 }}
      >
        <ControlButton onClick={onRefresh} icon={RefreshCw} label="Refresh" />
        <ControlButton onClick={onResetZoom} icon={Maximize2} label="Reset view" />
        <ControlButton
          onClick={() => onFocusModeChange(!focusMode)}
          icon={Focus}
          label="Focus mode"
          active={focusMode}
        />
      </motion.div>

      <motion.div
        className="flex flex-wrap gap-1.5 rounded-xl border border-border bg-card/95 p-1.5 shadow-sm backdrop-blur-sm"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.08 }}
      >
        <Filter className="mx-1 h-3.5 w-3.5 self-center text-muted-foreground" />
        {HEALTH_FILTERS.map((f) => (
          <button
            key={f.id}
            type="button"
            onClick={() => onHealthFilterChange(f.id)}
            className={cn(
              "flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[10px] font-medium uppercase tracking-wide transition-all duration-200",
              healthFilter === f.id
                ? "bg-muted text-foreground shadow-sm"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            <span className={cn("h-1.5 w-1.5 rounded-full", f.dot)} />
            {f.label}
          </button>
        ))}
      </motion.div>
    </motion.div>
  );
}

function ControlButton({
  onClick,
  icon: Icon,
  label,
  active,
}: {
  onClick: () => void;
  icon: typeof Search;
  label: string;
  active?: boolean;
}) {
  return (
    <motion.button
      type="button"
      onClick={onClick}
      title={label}
      whileHover={{ scale: 1.04 }}
      whileTap={{ scale: 0.96 }}
      transition={springSnappy}
      className={cn(
        "rounded-xl border border-border bg-card/95 p-2.5 text-muted-foreground shadow-sm backdrop-blur-sm transition-colors",
        active
          ? "border-border bg-muted text-foreground"
          : "hover:bg-muted hover:text-foreground",
      )}
    >
      <Icon className="h-4 w-4" />
    </motion.button>
  );
}
