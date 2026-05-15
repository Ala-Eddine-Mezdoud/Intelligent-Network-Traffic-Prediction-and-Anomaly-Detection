"use client";

/**
 * TopologyGraph.tsx
 *
 * A D3 force-directed graph rendered inside a React component.
 * Topology is fetched live from GET /api/topology (Flask + Mininet backend).
 *
 * Features:
 *   - Nodes colored by zone, shaped by type
 *   - Drag, zoom, and pan
 *   - Hover tooltip with node name, IP, zone
 *   - Zone legend
 *   - Loading skeleton and error state with retry
 */

import { useCallback, useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import {
  ZONE_META,
  type TopoNode,
  type TopoLink,
  type NodeZone,
} from "@/lib/topology-data";
import { getTopology } from "@/lib/simulation-api";

// ─── Tooltip state ────────────────────────────────────────────────────────────

interface TooltipState {
  x: number;
  y: number;
  node: TopoNode;
}

// ─── D3 simulation types ──────────────────────────────────────────────────────

interface SimNode extends TopoNode, d3.SimulationNodeDatum {}
interface SimLink extends d3.SimulationLinkDatum<SimNode> {
  source: SimNode | string;
  target: SimNode | string;
  kind?: "data" | "control";
}

// ─── Node visual helpers ──────────────────────────────────────────────────────

function nodeRadius(n: SimNode): number {
  if (n.type === "switch" || n.type === "controller") return 20;
  if (n.type === "router") return 17;
  return 11;
}

function nodeColor(node: SimNode): string {
  // Use health status if available, otherwise fall back to zone color
  if (node.health === "healthy") return "#10b981"; // green
  if (node.health === "warning") return "#f59e0b"; // orange
  if (node.health === "critical") return "#ef4444"; // red
  return ZONE_META[node.zone]?.color ?? "#94a3b8";
}

function nodeSymbol(type: string, r: number): string {
  if (type === "switch" || type === "controller") {
    const s = r * 1.3;
    return `M${-s},${-s} h${s * 2} v${s * 2} h${-s * 2} Z`;
  }
  if (type === "router") {
    return `M0,${-r * 1.4} L${r * 1.4},0 L0,${r * 1.4} L${-r * 1.4},0 Z`;
  }
  return "";
}

// ─── Graph renderer (pure D3, called once data is ready) ─────────────────────

function renderGraph(
  svgEl: SVGSVGElement,
  containerEl: HTMLDivElement,
  nodes: TopoNode[],
  links: TopoLink[],
  onTooltip: (t: TooltipState | null) => void,
): () => void {
  const W = containerEl.clientWidth || 800;
  const H = containerEl.clientHeight || 600;

  const svg = d3
    .select(svgEl)
    .attr("width", W)
    .attr("height", H)
    .attr("viewBox", `0 0 ${W} ${H}`);

  svg.selectAll("*").remove();

  // Glow filter for hover
  const defs = svg.append("defs");
  const filter = defs.append("filter").attr("id", "glow");
  filter
    .append("feGaussianBlur")
    .attr("stdDeviation", "3")
    .attr("result", "blur");
  const feMerge = filter.append("feMerge");
  feMerge.append("feMergeNode").attr("in", "blur");
  feMerge.append("feMergeNode").attr("in", "SourceGraphic");

  const g = svg.append("g").attr("class", "graph-root");

  // Zoom + pan
  const zoom = d3
    .zoom<SVGSVGElement, unknown>()
    .scaleExtent([0.25, 4])
    .on("zoom", (event) => g.attr("transform", event.transform));
  svg.call(zoom);

  // Clone data for D3 mutation
  const simNodes: SimNode[] = nodes.map((n) => ({ ...n }));
  const nodeById = new Map(simNodes.map((n) => [n.id, n]));
  const simLinks: SimLink[] = links.map((l) => ({
    source: nodeById.get(l.source)!,
    target: nodeById.get(l.target)!,
    kind: l.kind,
  }));

  // Force simulation
  const sim = d3
    .forceSimulation<SimNode>(simNodes)
    .force(
      "link",
      d3
        .forceLink<SimNode, SimLink>(simLinks)
        .id((d) => d.id)
        .distance((l) => {
          const s = l.source as SimNode;
          const t = l.target as SimNode;
          if ((l as SimLink).kind === "control") return 200;
          if (s.zone === "backbone" || t.zone === "backbone") return 150;
          return 90;
        }),
    )
    .force("charge", d3.forceManyBody().strength(-350))
    .force("center", d3.forceCenter(W / 2, H / 2))
    .force(
      "collision",
      d3.forceCollide<SimNode>().radius((d) => nodeRadius(d) + 8),
    );

  // Animated traffic particles
  const particleGroup = g.append("g").attr("class", "particles");

  // Create animated particles for data links
  const dataLinks = simLinks.filter((l) => (l as SimLink).kind !== "control");
  const particles = particleGroup
    .selectAll("circle")
    .data(dataLinks)
    .join("circle")
    .attr("r", 2)
    .attr("fill", "#67e8f9")
    .attr("opacity", 0.8);

  // Animation function for particles
  function animateParticles() {
    particles
      .attr("cx", (d) => {
        const source = d.source as SimNode;
        const target = d.target as SimNode;
        const progress = (Date.now() / 2000) % 1; // 2 second cycle
        return source.x! + (target.x! - source.x!) * progress;
      })
      .attr("cy", (d) => {
        const source = d.source as SimNode;
        const target = d.target as SimNode;
        const progress = (Date.now() / 2000) % 1;
        return source.y! + (target.y! - source.y!) * progress;
      });
  }

  // Start particle animation
  const animationId = setInterval(animateParticles, 50);

  // Nodes
  const nodeGroup = g.append("g").attr("class", "nodes");

  const nodeEl = nodeGroup
    .selectAll<SVGGElement, SimNode>("g")
    .data(simNodes)
    .join("g")
    .attr("cursor", "pointer")
    .call(
      d3
        .drag<SVGGElement, SimNode>()
        .on("start", (event, d) => {
          if (!event.active) sim.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on("drag", (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on("end", (event, d) => {
          if (!event.active) sim.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        }),
    )
    .on("mouseenter", function (event, d) {
      d3.select(this).select(".node-shape").attr("filter", "url(#glow)");
      const rect = svgEl.getBoundingClientRect();
      onTooltip({
        x: event.clientX - rect.left,
        y: event.clientY - rect.top,
        node: d,
      });
    })
    .on("mouseleave", function () {
      d3.select(this).select(".node-shape").attr("filter", null);
      onTooltip(null);
    });

  nodeEl.each(function (d) {
    const el = d3.select(this);
    const r = nodeRadius(d);
    const color = nodeColor(d);

    if (d.type === "switch" || d.type === "router" || d.type === "controller") {
      el.append("path")
        .attr("class", "node-shape")
        .attr("d", nodeSymbol(d.type, r))
        .attr("fill", color)
        .attr("stroke", "#0f172a")
        .attr("stroke-width", 1.5);
    } else {
      el.append("circle")
        .attr("class", "node-shape")
        .attr("r", r)
        .attr("fill", color)
        .attr("stroke", "#0f172a")
        .attr("stroke-width", 1);
    }

    const showLabel =
      d.type === "switch" ||
      d.type === "router" ||
      d.type === "controller" ||
      d.type === "security" ||
      d.id === "dc_web" ||
      d.id === "dc_vpn";

    if (showLabel) {
      el.append("text")
        .attr("text-anchor", "middle")
        .attr("dy", r + 13)
        .attr("font-size", "9px")
        .attr("font-family", "ui-monospace, monospace")
        .attr("fill", color)
        .attr("opacity", 0.85)
        .text(d.id);
    }
  });

  sim.on("tick", () => {
    linkEl
      .attr("x1", (d) => (d.source as SimNode).x!)
      .attr("y1", (d) => (d.source as SimNode).y!)
      .attr("x2", (d) => (d.target as SimNode).x!)
      .attr("y2", (d) => (d.target as SimNode).y!);

    nodeEl.attr("transform", (d) => `translate(${d.x},${d.y})`);
  });

  return () => {
    sim.stop();
    clearInterval(animationId);
  };
}

// ─── Component ────────────────────────────────────────────────────────────────

export function TopologyGraph() {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);

  // Fetch state
  const [nodes, setNodes] = useState<TopoNode[] | null>(null);
  const [links, setLinks] = useState<TopoLink[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTopology = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getTopology();
      setNodes(data.nodes);
      setLinks(data.links);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load topology");
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch on mount
  useEffect(() => {
    fetchTopology();
  }, [fetchTopology]);

  // Render D3 graph once data is ready
  useEffect(() => {
    if (!nodes || !links || !svgRef.current || !containerRef.current) return;
    const cleanup = renderGraph(
      svgRef.current,
      containerRef.current,
      nodes,
      links,
      setTooltip,
    );
    return cleanup;
  }, [nodes, links]);

  return (
    <div ref={containerRef} className="relative w-full h-full">
      {/* Loading state */}
      {loading && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-white/5 backdrop-blur-md z-20">
          <div className="w-8 h-8 rounded-full border-2 border-zinc-600 border-t-blue-400 animate-spin" />
          <p className="text-xs font-mono text-zinc-400">
            Fetching topology from Mininet…
          </p>
        </div>
      )}

      {/* Error state */}
      {!loading && error && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 z-20">
          <p className="text-xs font-mono text-red-400">{error}</p>
          <button
            onClick={fetchTopology}
            className="text-xs font-mono px-3 py-1.5 rounded border border-zinc-600 text-zinc-300 hover:border-zinc-400 hover:text-white transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* D3 canvas */}
      <svg
        ref={svgRef}
        className="w-full h-full bg-transparent"
        style={{ display: "block" }}
      />

      {/* Hover tooltip */}
      {tooltip && (
        <div
          className="pointer-events-none absolute z-10 rounded-md border border-border bg-white/10 backdrop-blur-md px-3 py-2 text-xs font-mono shadow-xl text-white"
          style={{
            left: tooltip.x + 12,
            top: tooltip.y - 8,
            transform: "translateY(-50%)",
          }}
        >
          <p className="font-semibold text-white mb-1">{tooltip.node.id}</p>
          <p>
            <span className="text-zinc-400">type: </span>
            <span style={{ color: nodeColor(tooltip.node) }}>
              {tooltip.node.type}
            </span>
          </p>
          <p>
            <span className="text-zinc-400">zone: </span>
            <span style={{ color: nodeColor(tooltip.node) }}>
              {ZONE_META[tooltip.node.zone]?.label}
            </span>
          </p>
          {tooltip.node.health && (
            <p>
              <span className="text-zinc-400">health: </span>
              <span style={{ color: nodeColor(tooltip.node) }}>
                {tooltip.node.health}
              </span>
            </p>
          )}
          {tooltip.node.ip && (
            <p>
              <span className="text-zinc-400">ip: </span>
              <span className="text-zinc-200">{tooltip.node.ip}</span>
            </p>
          )}
        </div>
      )}

      {/* Zone legend */}
      {!loading && !error && (
        <div className="absolute bottom-3 left-3 flex flex-col gap-1 bg-white/5 backdrop-blur-md border border-border rounded-md px-3 py-2 text-xs font-mono text-zinc-100">
          {(
            Object.entries(ZONE_META) as [
              NodeZone,
              (typeof ZONE_META)[NodeZone],
            ][]
          ).map(([zone, meta]) => (
            <div key={zone} className="flex items-center gap-2">
              <span
                className="inline-block w-2 h-2 rounded-full"
                style={{ backgroundColor: meta.color }}
              />
              <span style={{ color: meta.color }}>{meta.label}</span>
            </div>
          ))}
          <hr className="border-border my-1" />
          <div className="flex items-center gap-4 text-zinc-400">
            <span>■ switch</span>
            <span>◆ router</span>
            <span>● host</span>
          </div>
        </div>
      )}
    </div>
  );
}
