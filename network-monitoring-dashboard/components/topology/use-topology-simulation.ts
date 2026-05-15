"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import * as d3 from "d3";
import type { TopoNode, TopoLink, NodeZone } from "@/lib/topology-data";

export type SimNode = TopoNode & {
  x: number;
  y: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
};

export type SimLink = d3.SimulationLinkDatum<SimNode> & {
  kind?: "data" | "control";
};

const ZONE_ANCHORS: Record<NodeZone, { x: number; y: number }> = {
  backbone: { x: 0, y: -80 },
  datacenter: { x: -220, y: 40 },
  "enterprise-a": { x: 180, y: -40 },
  "enterprise-b": { x: 220, y: 80 },
  "home-a": { x: -160, y: 140 },
  "home-b": { x: 160, y: 160 },
  "control-plane": { x: 0, y: 120 },
};

export function useTopologySimulation(
  rawNodes: TopoNode[],
  rawLinks: TopoLink[],
  width: number,
  height: number,
) {
  const [nodes, setNodes] = useState<SimNode[]>([]);
  const [links, setLinks] = useState<SimLink[]>([]);
  const [tick, setTick] = useState(0);
  const simRef = useRef<d3.Simulation<SimNode, SimLink> | null>(null);
  const nodesRef = useRef<SimNode[]>([]);

  useEffect(() => {
    if (!width || !height || rawNodes.length === 0) return;

    const cx = width / 2;
    const cy = height / 2;

    const initial: SimNode[] = rawNodes.map((n, i) => {
      const anchor = ZONE_ANCHORS[n.zone] ?? { x: 0, y: 0 };
      const angle = (i / rawNodes.length) * Math.PI * 2;
      return {
        ...n,
        x: cx + anchor.x + Math.cos(angle) * 40,
        y: cy + anchor.y + Math.sin(angle) * 40,
      };
    });

    const nodeById = new Map(initial.map((n) => [n.id, n]));
    const linkData: SimLink[] = rawLinks
      .map((l) => {
        const sourceId = typeof l.source === "string" ? l.source : String(l.source);
        const targetId = typeof l.target === "string" ? l.target : String(l.target);
        const source = nodeById.get(sourceId);
        const target = nodeById.get(targetId);
        if (!source || !target) return null;
        return { source, target, kind: l.kind } as SimLink;
      })
      .filter(Boolean) as SimLink[];

    nodesRef.current = initial;
    setNodes(initial);
    setLinks(linkData);

    simRef.current?.stop();

    const simulation = d3
      .forceSimulation<SimNode>(nodesRef.current)
      .force(
        "link",
        d3
          .forceLink<SimNode, SimLink>(linkData)
          .id((d) => d.id)
          .distance(100)
          .strength(0.4),
      )
      .force("charge", d3.forceManyBody().strength(-320))
      .force("center", d3.forceCenter(cx, cy).strength(0.08))
      .force("collision", d3.forceCollide<SimNode>().radius(36))
      .force("zone", () => {
        for (const node of nodesRef.current) {
          const anchor = ZONE_ANCHORS[node.zone];
          if (!anchor) continue;
          node.vx = (node.vx ?? 0) + (cx + anchor.x - node.x) * 0.002;
          node.vy = (node.vy ?? 0) + (cy + anchor.y - node.y) * 0.002;
        }
      });

    let frame = 0;
    simulation.on("tick", () => {
      frame += 1;
      if (frame % 2 === 0) setTick((t) => t + 1);
    });

    simRef.current = simulation;

    return () => {
      simulation.stop();
    };
  }, [rawNodes, rawLinks, width, height]);

  const drag = useCallback(
    (nodeId: string) =>
      d3
        .drag<SVGGElement, unknown>()
        .on("start", () => {
          const n = nodesRef.current.find((x) => x.id === nodeId);
          if (!n) return;
          n.fx = n.x;
          n.fy = n.y;
          simRef.current?.alphaTarget(0.25).restart();
        })
        .on("drag", (event) => {
          const n = nodesRef.current.find((x) => x.id === nodeId);
          if (!n) return;
          n.fx = event.x;
          n.fy = event.y;
        })
        .on("end", () => {
          const n = nodesRef.current.find((x) => x.id === nodeId);
          if (!n) return;
          n.fx = null;
          n.fy = null;
          simRef.current?.alphaTarget(0);
        }),
    [],
  );

  const displayNodes = nodesRef.current.length ? nodesRef.current : nodes;
  const displayLinks = links.map((l) => ({
    ...l,
    source:
      typeof l.source === "object"
        ? l.source
        : displayNodes.find((n) => n.id === l.source)!,
    target:
      typeof l.target === "object"
        ? l.target
        : displayNodes.find((n) => n.id === l.target)!,
  }));

  return {
    nodes: displayNodes,
    links: displayLinks,
    tick,
    drag,
    simRef,
  };
}
