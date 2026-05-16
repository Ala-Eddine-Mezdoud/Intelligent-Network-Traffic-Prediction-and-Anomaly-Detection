"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as d3 from "d3";
import { motion } from "framer-motion";
import { TopoNode, TopoLink, NodeZone } from "@/lib/topology-data";
import { getTopology } from "@/lib/simulation-api";
import { NodeRenderer } from "./node-renderer";
import { LinkRenderer } from "./link-renderer";
import { ZoneOverlay } from "./zone-overlay";
import { SidePanel } from "./side-panel";
import {
  TopologyControls,
  type HealthFilter,
} from "./topology-controls";
import { Tooltip } from "./tooltip";
import { useTopologySimulation, type SimNode } from "./use-topology-simulation";
import { GRAPH_COLORS } from "./graph-constants";
import { TopologySkeleton } from "@/components/skeletons";
import { fadeIn } from "@/lib/motion";

function matchesSearch(node: TopoNode, query: string) {
  if (!query.trim()) return false;
  const q = query.toLowerCase();
  return (
    node.id.toLowerCase().includes(q) ||
    (node.ip?.toLowerCase().includes(q) ?? false)
  );
}

export function TopologyGraph() {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const [rawNodes, setRawNodes] = useState<TopoNode[]>([]);
  const [rawLinks, setRawLinks] = useState<TopoLink[]>([]);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedNode, setSelectedNode] = useState<TopoNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<TopoNode | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [searchQuery, setSearchQuery] = useState("");
  const [healthFilter, setHealthFilter] = useState<HealthFilter>("all");
  const [focusMode, setFocusMode] = useState(false);
  const [transform, setTransform] = useState(d3.zoomIdentity);

  const { nodes, links, tick, drag } = useTopologySimulation(
    rawNodes,
    rawLinks,
    dimensions.width,
    dimensions.height,
  );

  const fetchData = useCallback(async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      const data = await getTopology();
      setRawNodes(data.nodes);
      setRawLinks(data.links);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load topology");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(() => fetchData(true), 15000);
    return () => clearInterval(interval);
  }, [fetchData]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      setDimensions({
        width: Math.max(width, 320),
        height: Math.max(height, 400),
      });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    if (!svgRef.current) return;
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.15, 3.5])
      .on("zoom", (event) => setTransform(event.transform));

    const svg = d3.select(svgRef.current);
    svg.call(zoom);
    return () => {
      svg.on(".zoom", null);
    };
  }, []);

  const searchMatchIds = useMemo(() => {
    if (!searchQuery.trim()) return new Set<string>();
    return new Set(nodes.filter((n) => matchesSearch(n, searchQuery)).map((n) => n.id));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchQuery, nodes, tick]);

  const focusNeighborIds = useMemo(() => {
    if (!focusMode || !selectedNode) return new Set<string>();
    const ids = new Set<string>([selectedNode.id]);
    for (const link of links) {
      const s = link.source as SimNode;
      const t = link.target as SimNode;
      if (s.id === selectedNode.id) ids.add(t.id);
      if (t.id === selectedNode.id) ids.add(s.id);
    }
    return ids;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusMode, selectedNode, links, tick]);

  const zones = useMemo(() => {
    const groups: Partial<Record<NodeZone, SimNode[]>> = {};
    for (const n of nodes) {
      if (!groups[n.zone]) groups[n.zone] = [];
      groups[n.zone]!.push(n);
    }
    return Object.entries(groups).map(([id, zoneNodes]) => ({
      id: id as NodeZone,
      label: id.replace(/-/g, " "),
      nodes: zoneNodes ?? [],
    }));
  }, [nodes, tick]);

  const handleResetZoom = () => {
    if (!svgRef.current) return;
    d3.select(svgRef.current)
      .transition()
      .duration(600)
      .ease(d3.easeCubicOut)
      .call(
        d3.zoom<SVGSVGElement, unknown>().transform as never,
        d3.zoomIdentity,
      );
  };

  const isNodeVisible = (node: TopoNode) =>
    healthFilter === "all" || node.health === healthFilter;

  const isNodeDimmed = (node: TopoNode) => {
    if (searchQuery.trim() && searchMatchIds.size > 0 && !searchMatchIds.has(node.id)) {
      return true;
    }
    if (focusMode && focusNeighborIds.size > 0 && !focusNeighborIds.has(node.id)) {
      return true;
    }
    return false;
  };

  if (loading && rawNodes.length === 0) {
    return <TopologySkeleton className="h-full min-h-[480px]" />;
  }

  if (error && rawNodes.length === 0) {
    return (
      <motion.div
        variants={fadeIn}
        initial="hidden"
        animate="visible"
        className="flex h-full min-h-[480px] flex-col items-center justify-center rounded-2xl border border-border bg-muted"
      >
        <p className="text-sm font-medium text-foreground">Unable to load topology</p>
        <p className="mt-1 text-xs text-muted-foreground">{error}</p>
        <button
          type="button"
          onClick={fetchData}
          className="mt-4 rounded-xl border border-border bg-card px-4 py-2 text-xs font-medium text-foreground shadow-sm transition-colors hover:bg-muted"
        >
          Retry
        </button>
      </motion.div>
    );
  }

  return (
    <motion.div
      ref={containerRef}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="relative h-full w-full min-h-[480px] overflow-hidden rounded-2xl border border-border bg-card shadow-sm"
    >
      <motion.div
        className="pointer-events-none absolute inset-0 opacity-[0.35]"
        style={{
          backgroundImage: `linear-gradient(${GRAPH_COLORS.grid} 1px, transparent 1px), linear-gradient(90deg, ${GRAPH_COLORS.grid} 1px, transparent 1px)`,
          backgroundSize: "40px 40px",
          transform: `translate(${transform.x % 40}px, ${transform.y % 40}px)`,
        }}
      />

      <svg
        ref={svgRef}
        width={dimensions.width}
        height={dimensions.height}
        className="h-full w-full cursor-grab touch-none active:cursor-grabbing"
        onMouseMove={(e) => setMousePos({ x: e.clientX, y: e.clientY })}
      >
        <g transform={transform.toString()}>
          <ZoneOverlay zones={zones} />

          {links.map((link, i) => {
            const source = link.source as SimNode;
            const target = link.target as SimNode;
            const linkDimmed =
              (searchMatchIds.size > 0 &&
                !searchMatchIds.has(source.id) &&
                !searchMatchIds.has(target.id)) ||
              (focusMode &&
                focusNeighborIds.size > 0 &&
                !focusNeighborIds.has(source.id) &&
                !focusNeighborIds.has(target.id));

            return (
              <LinkRenderer
                key={`${source.id}-${target.id}-${i}`}
                link={{ source, target, kind: link.kind }}
                isHighlighted={
                  searchMatchIds.has(source.id) || searchMatchIds.has(target.id)
                }
                isDimmed={linkDimmed}
                showTraffic
                index={i}
              />
            );
          })}

          {nodes.map((node) => {
            if (!isNodeVisible(node)) return null;
            return (
              <g
                key={node.id}
                className="node-group"
                transform={`translate(${node.x},${node.y})`}
                onClick={() => setSelectedNode(node)}
                onMouseEnter={() => setHoveredNode(node)}
                onMouseLeave={() => setHoveredNode(null)}
                ref={(el) => {
                  if (el) d3.select(el).call(drag(node.id) as never);
                }}
              >
                <NodeRenderer
                  node={node}
                  isFocused={selectedNode?.id === node.id}
                  isHovered={
                    hoveredNode?.id === node.id || searchMatchIds.has(node.id)
                  }
                  isDimmed={isNodeDimmed(node)}
                />
              </g>
            );
          })}
        </g>
      </svg>

      <TopologyControls
        onSearch={setSearchQuery}
        onResetZoom={handleResetZoom}
        onRefresh={fetchData}
        focusMode={focusMode}
        onFocusModeChange={setFocusMode}
        healthFilter={healthFilter}
        onHealthFilterChange={setHealthFilter}
      />

      <SidePanel node={selectedNode} onClose={() => setSelectedNode(null)} />

      <Tooltip node={hoveredNode && !selectedNode ? hoveredNode : null} x={mousePos.x} y={mousePos.y} />

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="absolute bottom-4 left-4 rounded-xl border border-border bg-card/95 p-3 shadow-sm backdrop-blur-sm"
      >
        <div className="flex flex-wrap items-center gap-4">
          <LegendItem color={GRAPH_COLORS.healthy} label="Healthy" />
          <LegendItem color={GRAPH_COLORS.warning} label="Warning" />
          <LegendItem color={GRAPH_COLORS.critical} label="Critical" />
          <LegendItem color={GRAPH_COLORS.neutral} label="Inactive" />
        </div>
      </motion.div>
    </motion.div>
  );
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <motion.div
      className="flex items-center gap-1.5"
      whileHover={{ scale: 1.03 }}
      transition={{ type: "spring", stiffness: 400, damping: 30 }}
    >
      <motion.div
        className="h-2 w-2 rounded-full"
        style={{ backgroundColor: color }}
        animate={{ scale: [1, 1.15, 1] }}
        transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
      />
      <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
    </motion.div>
  );
}
