const svg = d3.select("#topology");

const selected = [];
let topologyData = null;
let activePath = [];
let linkSel = null;
let nodeSel = null;
let labelSel = null;
let currentCaptureId = null;
let controlOnlyMode = false;

function getNumericField(id, fallback = 0) {
    const el = document.getElementById(id);
    if (!el) {
        return fallback;
    }
    const value = Number(el.value);
    return Number.isFinite(value) ? value : fallback;
}

function setFieldValue(id, value) {
    const el = document.getElementById(id);
    if (!el) {
        return;
    }
    el.value = value;
}

function collectRealtimeSettingsFromForm() {
    return {
        attack_interval_min_seconds: Math.floor(getNumericField("rtAttackMin", 60)),
        attack_interval_max_seconds: Math.floor(getNumericField("rtAttackMax", 300)),
        attack_intensity: getNumericField("rtAttackIntensity", 1.0),
        protocol_mix_weights: {
            icmp: Math.floor(getNumericField("rtWIcmp", 55)),
            http: Math.floor(getNumericField("rtWHttp", 75)),
            dns: Math.floor(getNumericField("rtWDns", 65)),
            dhcp: Math.floor(getNumericField("rtWDhcp", 40)),
            quic_udp: Math.floor(getNumericField("rtWQuic", 60)),
            ftp: Math.floor(getNumericField("rtWFtp", 35)),
            ssh: Math.floor(getNumericField("rtWSsh", 45)),
            igmp: Math.floor(getNumericField("rtWIgmp", 25)),
        },
    };
}

function applyRealtimeSettingsToForm(settings) {
    if (!settings) {
        return;
    }

    setFieldValue("rtAttackMin", settings.attack_interval_min_seconds ?? 60);
    setFieldValue("rtAttackMax", settings.attack_interval_max_seconds ?? 300);
    setFieldValue("rtAttackIntensity", settings.attack_intensity ?? 1.0);

    const mix = settings.protocol_mix_weights || {};
    setFieldValue("rtWIcmp", mix.icmp ?? 55);
    setFieldValue("rtWHttp", mix.http ?? 75);
    setFieldValue("rtWDns", mix.dns ?? 65);
    setFieldValue("rtWDhcp", mix.dhcp ?? 40);
    setFieldValue("rtWQuic", mix.quic_udp ?? 60);
    setFieldValue("rtWFtp", mix.ftp ?? 35);
    setFieldValue("rtWSsh", mix.ssh ?? 45);
    setFieldValue("rtWIgmp", mix.igmp ?? 25);
}

const TYPE_COLORS = {
    switch: "#1467b3",
    router: "#8f3fc0",
    controller: "#d93a63",
    enterprise: "#248455",
    home: "#239a9f",
    server: "#cb7621",
    dns: "#0c7f8e",
    dhcp: "#ac7b00",
    iot: "#7a5b2f",
    security: "#bf334f",
};

const ZONE_COLORS = {
    backbone: "#b8d8f2",
    "control-plane": "#f8c7d4",
    "enterprise-a": "#c9ecd5",
    "enterprise-b": "#cee8d3",
    "home-a": "#c7eef2",
    "home-b": "#bde8ee",
    datacenter: "#f8dfc2",
};

function isInfraNode(node) {
    return node.type === "switch" || node.type === "router" || node.type === "controller";
}

function isInfraType(type) {
    return type === "switch" || type === "router" || type === "controller";
}

function zoneAnchors(width, height) {
    return {
        "control-plane": { x: width * 0.5, y: height * 0.08 },
        backbone: { x: width * 0.5, y: height * 0.28 },
        "enterprise-a": { x: width * 0.2, y: height * 0.48 },
        "enterprise-b": { x: width * 0.2, y: height * 0.76 },
        "home-a": { x: width * 0.8, y: height * 0.48 },
        "home-b": { x: width * 0.8, y: height * 0.76 },
        datacenter: { x: width * 0.5, y: height * 0.9 },
    };
}

function zoneBands(width, height) {
    return [
        { zone: "control-plane", x: width * 0.32, y: height * 0.02, w: width * 0.36, h: height * 0.12 },
        { zone: "backbone", x: width * 0.34, y: height * 0.15, w: width * 0.32, h: height * 0.2 },
        { zone: "enterprise-a", x: width * 0.04, y: height * 0.32, w: width * 0.32, h: height * 0.3 },
        { zone: "enterprise-b", x: width * 0.04, y: height * 0.62, w: width * 0.32, h: height * 0.31 },
        { zone: "home-a", x: width * 0.64, y: height * 0.32, w: width * 0.32, h: height * 0.3 },
        { zone: "home-b", x: width * 0.64, y: height * 0.62, w: width * 0.32, h: height * 0.31 },
        { zone: "datacenter", x: width * 0.32, y: height * 0.78, w: width * 0.36, h: height * 0.2 },
    ];
}

function applyControlFocusMode() {
    if (!linkSel || !nodeSel || !labelSel) {
        return;
    }

    linkSel.style("display", (d) => (controlOnlyMode && d.kind !== "control" ? "none" : null));

    nodeSel.classed("muted-node", (d) => {
        if (!controlOnlyMode) {
            return false;
        }
        return !isInfraType(d.type);
    });

    labelSel.classed("muted-label", (d) => {
        if (!controlOnlyMode) {
            return false;
        }
        return !isInfraType(d.type);
    });
}

function normalizeLink(a, b) {
    // D3 mutates link endpoints from ids to objects; normalize both cases.
    const left = typeof a === "object" ? a.id : a;
    const right = typeof b === "object" ? b.id : b;
    return [left, right].sort().join("--");
}

function renderChips(containerId, items, colorFromItem) {
    const container = document.getElementById(containerId);
    container.innerHTML = "";

    items.forEach((item) => {
        const chip = document.createElement("span");
        chip.className = "chip";

        const dot = document.createElement("span");
        dot.className = "dot";
        dot.style.background = colorFromItem(item);

        const text = document.createElement("span");
        text.innerText = item;

        chip.appendChild(dot);
        chip.appendChild(text);
        container.appendChild(chip);
    });
}

function updateSummary(data) {
    const counts = data.nodes.reduce((acc, node) => {
        acc[node.type] = (acc[node.type] || 0) + 1;
        return acc;
    }, {});

    const zones = [...new Set(data.nodes.map((node) => node.zone))].sort();
    const typeBits = Object.keys(counts)
        .sort()
        .map((key) => `${key}:${counts[key]}`)
        .join(" | ");

    document.getElementById("summary").innerText =
        `nodes:${data.nodes.length} | links:${data.links.length} | zones:${zones.length}\n${typeBits}`;

    renderChips("legend", Object.keys(counts).sort(), (type) => TYPE_COLORS[type] || "#666");

    const zonePalette = ["#1f6fb0", "#a245ab", "#117a65", "#be6d1f", "#4a6ea9", "#7f5d3b"];
    renderChips("zones", zones, (zone) => zonePalette[Math.abs(hash(zone)) % zonePalette.length]);
}

function hash(text) {
    let value = 0;
    for (let i = 0; i < text.length; i += 1) {
        value = ((value << 5) - value + text.charCodeAt(i)) | 0;
    }
    return value;
}

function refreshSelectionStyles() {
    if (!nodeSel) {
        return;
    }
    nodeSel.classed("is-selected", (d) => selected.includes(d.id));
}

function applyPathHighlight(path) {
    activePath = path || [];
    if (!linkSel || !nodeSel) {
        return;
    }

    const pathSet = new Set();
    for (let i = 0; i < activePath.length - 1; i += 1) {
        pathSet.add(normalizeLink(activePath[i], activePath[i + 1]));
    }

    linkSel.classed("is-path", (d) => pathSet.has(normalizeLink(d.source, d.target)));
    nodeSel.classed("is-path-node", (d) => activePath.includes(d.id));
}

function clearPath() {
    applyPathHighlight([]);
    document.getElementById("pathInfo").innerText = "Path: cleared";
}

function draw(data) {
    svg.selectAll("*").remove();

    const rect = svg.node().getBoundingClientRect();
    const width = rect.width || 900;
    const height = rect.height || 600;

    const links = data.links.map((link) => ({ ...link }));
    const nodes = data.nodes.map((node) => ({ ...node }));
    const nodeMap = new Map(nodes.map((node) => [node.id, node]));
    const anchors = zoneAnchors(width, height);

    nodes.forEach((node) => {
        if (node.type === "controller") {
            node.fx = anchors["control-plane"].x;
            node.fy = anchors["control-plane"].y;
        }
    });

    const defs = svg.append("defs");
    defs
        .append("marker")
        .attr("id", "control-arrow")
        .attr("viewBox", "0 -5 10 10")
        .attr("refX", 18)
        .attr("refY", 0)
        .attr("markerWidth", 6)
        .attr("markerHeight", 6)
        .attr("orient", "auto")
        .append("path")
        .attr("d", "M0,-5L10,0L0,5")
        .attr("fill", "rgba(217, 58, 99, 0.86)");

    svg
        .append("g")
        .selectAll("rect")
        .data(zoneBands(width, height))
        .enter()
        .append("rect")
        .attr("class", "zone-band")
        .attr("x", (d) => d.x)
        .attr("y", (d) => d.y)
        .attr("width", (d) => d.w)
        .attr("height", (d) => d.h)
        .attr("fill", (d) => ZONE_COLORS[d.zone] || "#dfe7ee");

    svg
        .append("g")
        .selectAll("text")
        .data(zoneBands(width, height))
        .enter()
        .append("text")
        .attr("class", "zone-title")
        .attr("x", (d) => d.x + 12)
        .attr("y", (d) => d.y + 18)
        .text((d) => (d.zone === "control-plane" ? "CONTROL-PLANE (RYU)" : d.zone.toUpperCase()));

    const simulation = d3
        .forceSimulation(nodes)
        // Router-adjacent links are spaced farther for readability.
        .force("link", d3.forceLink(links).id((d) => d.id).distance((d) => (d.source.type === "router" || d.target.type === "router" ? 145 : 118)))
        .force("charge", d3.forceManyBody().strength(-760))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collision", d3.forceCollide().radius((d) => (isInfraNode(d) ? 28 : 20)))
        .force("x", d3.forceX((d) => (anchors[d.zone] ? anchors[d.zone].x : width / 2)).strength((d) => (isInfraNode(d) ? 0.38 : 0.16)))
        .force("y", d3.forceY((d) => (anchors[d.zone] ? anchors[d.zone].y : height / 2)).strength((d) => (isInfraNode(d) ? 0.42 : 0.18)));

    linkSel = svg
        .append("g")
        .selectAll("line")
        .data(links)
        .enter()
        .append("line")
        .attr("class", (d) => {
            if (d.kind === "control") {
                return "link control-link";
            }

            const source = nodeMap.get(d.source);
            const target = nodeMap.get(d.target);
            const sourceInfra = source ? isInfraType(source.type) : false;
            const targetInfra = target ? isInfraType(target.type) : false;

            if (sourceInfra && targetInfra) {
                return "link infra-link";
            }

            if (sourceInfra || targetInfra) {
                return "link uplink";
            }

            return "link";
        });

    nodeSel = svg
        .append("g")
        .selectAll("circle")
        .data(nodes)
        .enter()
        .append("circle")
        .attr("class", (d) => `node ${d.type} ${isInfraType(d.type) ? "infra" : "endpoint"}`)
        .attr("r", (d) => {
            if (d.type === "controller") {
                return 16;
            }
            if (d.type === "router") {
                return 21;
            }
            if (d.type === "switch") {
                return 19;
            }
            return 14;
        })
        .on("click", (event, d) => {
            if (d.type === "switch" || d.type === "router" || d.type === "controller") {
                document.getElementById("info").innerText = `${d.id} (${d.type}) is transit-only for selection`;
                return;
            }

            if (selected.length < 2) {
                selected.push(d.id);
            } else {
                selected.splice(0, selected.length, d.id);
            }

            document.getElementById("selected").innerText = selected.join(" -> ");
            document.getElementById("info").innerText = `${d.id} [${d.type}] in ${d.zone}`;
            refreshSelectionStyles();
        });

    labelSel = svg
        .append("g")
        .selectAll("text")
        .data(nodes)
        .enter()
        .append("text")
        .attr("class", (d) => `label ${isInfraType(d.type) ? "infra-label" : "endpoint-label"}`)
        .text((d) => d.id);

    simulation.on("tick", () => {
        linkSel
            .attr("x1", (d) => d.source.x)
            .attr("y1", (d) => d.source.y)
            .attr("x2", (d) => d.target.x)
            .attr("y2", (d) => d.target.y);

        nodeSel
            .attr("cx", (d) => {
                d.x = Math.max(26, Math.min(width - 26, d.x));
                return d.x;
            })
            .attr("cy", (d) => {
                d.y = Math.max(26, Math.min(height - 26, d.y));
                return d.y;
            });

        labelSel
            .attr("x", (d) => d.x + 9)
            .attr("y", (d) => d.y + 4);
    });

    refreshSelectionStyles();
    applyPathHighlight(activePath);
    updateSummary(data);
    applyControlFocusMode();
}

async function visualizePath() {
    if (selected.length !== 2) {
        alert("Select two endpoint nodes first.");
        return;
    }

    const response = await fetch("/api/path", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ src: selected[0], dst: selected[1] }),
    });

    const payload = await response.json();

    if (payload.error) {
        document.getElementById("pathInfo").innerText = `Path error: ${payload.error}`;
        applyPathHighlight([]);
        return;
    }

    applyPathHighlight(payload.path || []);
    document.getElementById("pathInfo").innerText = `Path: ${(payload.path || []).join(" -> ")}`;
}

async function pingPath() {
    if (selected.length !== 2) {
        alert("Select two endpoint nodes first.");
        return;
    }

    await visualizePath();

    const response = await fetch("/api/ping", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ src: selected[0], dst: selected[1] }),
    });

    const output = await response.text();
    document.getElementById("flows").innerText = output;
}

async function loadFlows() {
    const response = await fetch("/api/flows");
    const payload = await response.json();
    document.getElementById("flows").innerText = JSON.stringify(payload, null, 2);
}

async function loadTopology() {
    const response = await fetch("/api/topology");
    const payload = await response.json();

    if (payload.error) {
        document.getElementById("summary").innerText = payload.error;
        return;
    }

    topologyData = payload;
    draw(payload);
}

function updateLabStatusText(status) {
    // Show both current and last finished capture/export context.
    const bits = [];
    bits.push(`realtime:${status.realtime_running ? "running" : "idle"}`);
    if (status.realtime_interval_seconds) {
        bits.push(`interval:${status.realtime_interval_seconds}s`);
    }

    bits.push(`capture:${status.capture_running ? "running" : "idle"}`);
    bits.push(`traffic:${status.traffic_running ? "running" : "idle"}`);

    const captureId = status.capture_id || status.last_capture_id || "none";
    bits.push(`capture_id:${captureId}`);

    if (status.last_export_csv) {
        bits.push(`last_csv:${status.last_export_csv}`);
    }

    if (status.last_inference && status.last_inference.inference) {
        bits.push(`ai:${status.last_inference.inference.severity}`);
    }

    if (status.last_realtime_error) {
        bits.push(`rt_error:${status.last_realtime_error}`);
    }

    if (status.next_attack_profile) {
        bits.push(`next_attack:${status.next_attack_profile}`);
    }
    if (typeof status.next_attack_in_seconds === "number") {
        bits.push(`next_in:${status.next_attack_in_seconds}s`);
    }

    document.getElementById("labStatus").innerText = bits.join(" | ");

    if (status.last_capture_id) {
        currentCaptureId = status.last_capture_id;
    }
}

async function refreshLabStatus() {
    const response = await fetch("/api/lab/status");
    const payload = await response.json();

    if (payload.error) {
        document.getElementById("labStatus").innerText = `Lab error: ${payload.error}`;
        return;
    }

    updateLabStatusText(payload);
}

async function loadRealtimeSettings() {
    const response = await fetch("/api/pipeline/settings");
    const payload = await response.json();

    if (payload.error) {
        document.getElementById("labOutput").innerText = `Load settings failed: ${payload.error}`;
        return;
    }

    applyRealtimeSettingsToForm(payload);
    document.getElementById("labOutput").innerText = "Realtime settings loaded";
}

async function saveRealtimeSettings() {
    const settings = collectRealtimeSettingsFromForm();
    const response = await fetch("/api/pipeline/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
    });
    const payload = await response.json();

    if (payload.error) {
        document.getElementById("labOutput").innerText = `Save settings failed: ${payload.error}`;
        throw new Error(payload.error);
    }

    applyRealtimeSettingsToForm(payload);
    document.getElementById("labOutput").innerText = "Realtime settings saved";
    await refreshLabStatus();
}

async function startCapture() {
    // Timestamp label makes output files unique and traceable.
    const label = `cicids_${new Date().toISOString().replace(/[:.]/g, "-")}`;

    const response = await fetch("/api/lab/capture/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ label }),
    });
    const payload = await response.json();

    if (payload.error) {
        document.getElementById("labOutput").innerText = `Capture failed: ${payload.error}`;
        return;
    }

    currentCaptureId = payload.capture_id;
    document.getElementById("labOutput").innerText =
        `Capture started\nID: ${payload.capture_id}\nInterfaces: ${(payload.interfaces || []).join(", ")}`;

    await refreshLabStatus();
}

async function stopCapture() {
    const response = await fetch("/api/lab/capture/stop", { method: "POST" });
    const payload = await response.json();

    if (payload.error) {
        document.getElementById("labOutput").innerText = `Stop capture failed: ${payload.error}`;
        return;
    }

    if (payload.capture_id) {
        currentCaptureId = payload.capture_id;
    }

    document.getElementById("labOutput").innerText =
        `Capture stopped\nID: ${payload.capture_id || "none"}\nFiles: ${(payload.capture_files || []).length}`;

    await refreshLabStatus();
}

async function startTraffic() {
    const response = await fetch("/api/lab/traffic/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ duration_seconds: 90 }),
    });
    const payload = await response.json();

    if (payload.error) {
        document.getElementById("labOutput").innerText = `Traffic start failed: ${payload.error}`;
        return;
    }

    document.getElementById("labOutput").innerText =
        `Traffic simulation started for ${payload.duration_seconds || 90}s`;

    await refreshLabStatus();
}

async function stopTraffic() {
    const response = await fetch("/api/lab/traffic/stop", { method: "POST" });
    const payload = await response.json();

    if (payload.error) {
        document.getElementById("labOutput").innerText = `Traffic stop failed: ${payload.error}`;
        return;
    }

    document.getElementById("labOutput").innerText = "Traffic simulation stopped";

    await refreshLabStatus();
}

async function exportLabFeatures() {
    // Export uses the most recent capture id when available.
    const response = await fetch("/api/lab/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ capture_id: currentCaptureId }),
    });
    const payload = await response.json();

    if (payload.error) {
        document.getElementById("labOutput").innerText = `Export failed: ${payload.error}`;
        return;
    }

    document.getElementById("labOutput").innerText =
        `CSV exported\nCapture: ${payload.capture_id}\nFlows: ${payload.flow_count}\nPath: ${payload.csv_path}`;

    await refreshLabStatus();
}

async function relayToCollector() {
    const response = await fetch("/api/lab/relay", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ capture_id: currentCaptureId }),
    });
    const payload = await response.json();

    if (payload.error) {
        document.getElementById("labOutput").innerText = `Relay failed: ${payload.error}`;
        return;
    }

    document.getElementById("labOutput").innerText =
        `Relayed to collector\nCapture: ${payload.capture_id}\nFiles: ${(payload.relayed_files || []).length}\nInbox: ${payload.collector_inbox}`;

    await refreshLabStatus();
}

async function runInference() {
    const response = await fetch("/api/lab/infer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ capture_id: currentCaptureId }),
    });
    const payload = await response.json();

    if (payload.error) {
        document.getElementById("labOutput").innerText = `Inference failed: ${payload.error}`;
        return;
    }

    const inf = payload.inference || {};
    document.getElementById("labOutput").innerText =
        `AI inference completed\nCapture: ${payload.capture_id}\nFlows: ${payload.collector_flow_count}\nSeverity: ${inf.severity || "n/a"}\nRisk: ${inf.risk_score || 0}\nReport: ${payload.inference_path}`;

    await refreshLabStatus();
}

async function startRealtimePipeline() {
    await saveRealtimeSettings();

    const interval = Math.floor(getNumericField("rtInterval", 30));
    const response = await fetch("/api/pipeline/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ interval_seconds: interval }),
    });
    const payload = await response.json();

    if (payload.error) {
        document.getElementById("labOutput").innerText = `Realtime start failed: ${payload.error}`;
        return;
    }

    document.getElementById("labOutput").innerText =
        `Realtime pipeline started\nInterval: ${payload.interval_seconds || interval}s\nMode: capture -> relay -> AI infer`;

    await refreshLabStatus();
}

async function stopRealtimePipeline() {
    const response = await fetch("/api/pipeline/stop", { method: "POST" });
    const payload = await response.json();

    if (payload.error) {
        document.getElementById("labOutput").innerText = `Realtime stop failed: ${payload.error}`;
        return;
    }

    document.getElementById("labOutput").innerText = "Realtime pipeline stopped";

    await refreshLabStatus();
}

document.getElementById("btnPath").addEventListener("click", () => {
    visualizePath().catch((err) => {
        document.getElementById("pathInfo").innerText = `Path error: ${err}`;
    });
});

document.getElementById("btnPing").addEventListener("click", () => {
    pingPath().catch((err) => {
        document.getElementById("flows").innerText = `Ping failed: ${err}`;
    });
});

document.getElementById("btnClear").addEventListener("click", clearPath);
document.getElementById("btnFlows").addEventListener("click", () => {
    loadFlows().catch((err) => {
        document.getElementById("flows").innerText = `Flow API failed: ${err}`;
    });
});

document.getElementById("btnLabStartCapture").addEventListener("click", () => {
    startCapture().catch((err) => {
        document.getElementById("labOutput").innerText = `Capture start error: ${err}`;
    });
});

document.getElementById("btnLabStopCapture").addEventListener("click", () => {
    stopCapture().catch((err) => {
        document.getElementById("labOutput").innerText = `Capture stop error: ${err}`;
    });
});

document.getElementById("btnLabStartTraffic").addEventListener("click", () => {
    startTraffic().catch((err) => {
        document.getElementById("labOutput").innerText = `Traffic start error: ${err}`;
    });
});

document.getElementById("btnLabStopTraffic").addEventListener("click", () => {
    stopTraffic().catch((err) => {
        document.getElementById("labOutput").innerText = `Traffic stop error: ${err}`;
    });
});

document.getElementById("btnLabExport").addEventListener("click", () => {
    exportLabFeatures().catch((err) => {
        document.getElementById("labOutput").innerText = `Export error: ${err}`;
    });
});

document.getElementById("btnLabRelay").addEventListener("click", () => {
    relayToCollector().catch((err) => {
        document.getElementById("labOutput").innerText = `Relay error: ${err}`;
    });
});

document.getElementById("btnLabInfer").addEventListener("click", () => {
    runInference().catch((err) => {
        document.getElementById("labOutput").innerText = `Inference error: ${err}`;
    });
});

document.getElementById("btnPipelineStart").addEventListener("click", () => {
    startRealtimePipeline().catch((err) => {
        document.getElementById("labOutput").innerText = `Realtime start error: ${err}`;
    });
});

document.getElementById("btnPipelineStop").addEventListener("click", () => {
    stopRealtimePipeline().catch((err) => {
        document.getElementById("labOutput").innerText = `Realtime stop error: ${err}`;
    });
});

document.getElementById("btnRtLoadSettings").addEventListener("click", () => {
    loadRealtimeSettings().catch((err) => {
        document.getElementById("labOutput").innerText = `Load settings error: ${err}`;
    });
});

document.getElementById("btnRtSaveSettings").addEventListener("click", () => {
    saveRealtimeSettings().catch((err) => {
        document.getElementById("labOutput").innerText = `Save settings error: ${err}`;
    });
});

document.getElementById("btnToggleControl").addEventListener("click", () => {
    controlOnlyMode = !controlOnlyMode;
    document.getElementById("btnToggleControl").innerText =
        `Control Links Only: ${controlOnlyMode ? "On" : "Off"}`;
    applyControlFocusMode();
});

window.addEventListener("resize", () => {
    if (topologyData) {
        draw(topologyData);
    }
});

loadTopology().catch((err) => {
    document.getElementById("summary").innerText = `Topology unavailable: ${err}`;
});

refreshLabStatus().catch((err) => {
    document.getElementById("labStatus").innerText = `Lab status failed: ${err}`;
});

loadRealtimeSettings().catch(() => {});

window.setInterval(() => {
    refreshLabStatus().catch(() => {});
}, 4000);
