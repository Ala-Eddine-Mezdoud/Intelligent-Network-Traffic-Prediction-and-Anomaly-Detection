"use client";

import { motion } from "framer-motion";
import { NodeZone } from "@/lib/topology-data";
import { ZONE_STYLES } from "./graph-constants";

interface ZoneOverlayProps {
  zones: Array<{
    id: NodeZone;
    label: string;
    nodes: any[];
  }>;
}

export function ZoneOverlay({ zones }: ZoneOverlayProps) {
  return (
    <g className="pointer-events-none overflow-visible">
      {zones.map((zone) => {
        if (zone.nodes.length === 0) return null;

        // Calculate bounding box or center for the zone
        const xs = zone.nodes.map(n => n.x).filter(x => x !== undefined);
        const ys = zone.nodes.map(n => n.y).filter(y => y !== undefined);
        
        if (xs.length === 0 || ys.length === 0) return null;

        const minX = Math.min(...xs) - 60;
        const maxX = Math.max(...xs) + 60;
        const minY = Math.min(...ys) - 60;
        const maxY = Math.max(...ys) + 60;

        const width = maxX - minX;
        const height = maxY - minY;
        const style = ZONE_STYLES[zone.id] || ZONE_STYLES.backbone;

        return (
          <motion.g
            key={zone.id}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 1 }}
          >
            <rect
              x={minX}
              y={minY}
              width={width}
              height={height}
              rx={40}
              fill={style.color}
              fillOpacity={0.03}
              stroke={style.color}
              strokeOpacity={0.1}
              strokeWidth={1}
              strokeDasharray="10 10"
            />
            <text
              x={minX + 20}
              y={minY + 30}
              fill={style.color}
              fillOpacity={0.5}
              className="text-[10px] font-bold uppercase tracking-widest"
            >
              {zone.label}
            </text>
          </motion.g>
        );
      })}
    </g>
  );
}
