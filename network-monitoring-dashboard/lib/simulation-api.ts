import type { TopoNode, TopoLink } from "@/lib/topology-data";

const API_BASE = process.env.NEXT_PUBLIC_SDN_API_URL;
// Standard headers for all POST requests to Flask
const postHeaders = {
  "Content-Type": "application/json",
};

// ─── Topology ─────────────────────────────────────────────────────────────────

export interface TopologyResponse {
  nodes: TopoNode[];
  links: TopoLink[];
}

// Fetch the live topology from Mininet via the Flask backend.
// Returns nodes and links ready for the D3 graph.
export async function getTopology(): Promise<TopologyResponse> {
  const res = await fetch(`${API_BASE}/api/topology`);
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data?.error || `Topology fetch failed (${res.status})`);
  }
  const topologyData = await res.json();

  // Add mock health status to nodes for demonstration
  topologyData.nodes = topologyData.nodes.map((node: TopoNode) => ({
    ...node,
    health: getMockHealthStatus(node.id),
  }));

  return topologyData;
}

// Mock health status function - in production this would come from monitoring data
function getMockHealthStatus(
  nodeId: string,
): "healthy" | "warning" | "critical" {
  // Simulate some nodes having issues based on ID patterns
  if (nodeId.includes("switch") && Math.random() > 0.8) return "warning";
  if (nodeId.includes("router") && Math.random() > 0.9) return "critical";
  if (nodeId.includes("server") && Math.random() > 0.85) return "warning";
  return "healthy";
}

// ─── Lab controls ─────────────────────────────────────────────────────────────

// Fetch the current status of the Mininet simulation
export async function getLabStatus() {
  const res = await fetch(`${API_BASE}/api/lab/status`);
  return res.json();
}

// Start capturing packets in Mininet
export async function startCapture() {
  const res = await fetch(`${API_BASE}/api/lab/capture/start`, {
    method: "POST",
    headers: postHeaders,
    body: JSON.stringify({}), // Flask requires a JSON body, even if empty
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data?.error || "Failed to start capture");
  }
  return data;
}

// Stop capturing packets
export async function stopCapture() {
  const res = await fetch(`${API_BASE}/api/lab/capture/stop`, {
    method: "POST",
    headers: postHeaders,
    body: JSON.stringify({}),
  });
  return res.json();
}

// Generate synthetic traffic
export async function startTraffic(durationSeconds = 90) {
  const res = await fetch(`${API_BASE}/api/lab/traffic/start`, {
    method: "POST",
  });
  return res.json();
}

// Stop traffic generation
export async function stopTraffic() {
  const res = await fetch(`${API_BASE}/api/lab/traffic/stop`, {
    method: "POST",
    headers: postHeaders,
    body: JSON.stringify({}),
  });
  return res.json();
}

// Relay capture artifacts into collector inbox for inference
export async function relayCapture() {
  const res = await fetch(`${API_BASE}/api/lab/relay`, {
    method: "POST",
    headers: postHeaders,
    body: JSON.stringify({}),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data?.error || "Failed to relay capture");
  }
  return data;
}

// Extract features and run AI Inference
export async function runInference() {
  const res = await fetch(`${API_BASE}/api/lab/infer`, {
    method: "POST",
    headers: postHeaders,
    body: JSON.stringify({}),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data?.error || "Failed to run inference");
  }
  return data;
}
