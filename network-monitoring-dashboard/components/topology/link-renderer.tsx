"use client";

import { useMemo } from "react";
import { GRAPH_COLORS } from "./graph-constants";

interface LinkRendererProps {
  link: {
    source: { x?: number; y?: number; id?: string };
    target: { x?: number; y?: number; id?: string };
    kind?: "data" | "control";
    active?: boolean;
  };
  isHighlighted?: boolean;
  isDimmed?: boolean;
  showTraffic?: boolean;
  index?: number;
}

function buildPath(
  source: { x?: number; y?: number },
  target: { x?: number; y?: number },
) {
  if (source.x == null || source.y == null || target.x == null || target.y == null) {
    return "";
  }
  const dx = target.x - source.x;
  const dy = target.y - source.y;
  const dr = Math.sqrt(dx * dx + dy * dy) * 1.35;
  return `M${source.x},${source.y}A${dr},${dr} 0 0,1 ${target.x},${target.y}`;
}

export function LinkRenderer({
  link,
  isHighlighted,
  isDimmed,
  showTraffic = true,
  index = 0,
}: LinkRendererProps) {
  const path = useMemo(
    () => buildPath(link.source, link.target),
    [link.source.x, link.source.y, link.target.x, link.target.y],
  );

  if (!path) return null;

  const isControl = link.kind === "control";
  const strokeColor = isHighlighted
    ? GRAPH_COLORS.healthy
    : isDimmed
      ? "rgba(209, 213, 219, 0.35)"
      : GRAPH_COLORS.link;
  const showPacket =
    showTraffic && !isControl && link.active !== false && !isDimmed;

  return (
    <g className="pointer-events-none">
      <path
        d={path}
        fill="none"
        stroke={strokeColor}
        strokeWidth={isHighlighted ? 2 : 1}
        strokeDasharray={isControl ? "5 5" : undefined}
        opacity={isControl ? 0.45 : isDimmed ? 0.35 : 0.85}
      />
      {showPacket && (
        <>
          <circle r={2.5} fill={GRAPH_COLORS.particle} opacity={0.85}>
            <animateMotion
              dur={`${2.2 + (index % 4) * 0.35}s`}
              repeatCount="indefinite"
              path={path}
              begin={`${(index % 6) * 0.35}s`}
            />
          </circle>
          <circle r={1.5} fill={GRAPH_COLORS.healthy} opacity={0.5}>
            <animateMotion
              dur={`${3.4 + (index % 3) * 0.5}s`}
              repeatCount="indefinite"
              path={path}
              begin={`${1.1 + (index % 5) * 0.4}s`}
            />
          </circle>
        </>
      )}
    </g>
  );
}
