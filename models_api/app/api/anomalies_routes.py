"""
Anomalies API routes — migrated to use the GNN (TemporalGAT) model
from gnn_training_notebook instead of the old IDS sklearn pipeline.

CHANGED: entire inference backend replaced. The old pipeline was a
         scikit-learn joblib model (ids_pipeline.pkl) that consumed
         50 tabular network-flow features. The new model is a
         PyTorch Graph Neural Network (TemporalGAT) that consumes
         graph snapshots: sequences of [num_nodes × seq_len × 14]
         node-feature tensors plus a fixed edge_index topology.
         Both models classify network anomaly types, but the data
         shapes, loading mechanism, and inference path are entirely
         different.
"""

# ── Standard library ────────────────────────────────────────────────────────
import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── Third-party ──────────────────────────────────────────────────────────────
import numpy as np

# CHANGED: removed `joblib` (used to load ids_pipeline.pkl).
#          The GNN model is saved with torch.save(), so we need torch instead.
import torch
import torch.nn as nn
import torch.nn.functional as F

# CHANGED: added torch_geometric imports — required by TemporalGAT's
#          GATConv layers and the Data container used for graph inference.
from torch_geometric.data import Data
from torch_geometric.nn import GATConv

# ── FastAPI / internal ───────────────────────────────────────────────────────
from fastapi import APIRouter, Query

from app.schemas.anomalies import AnomalyItem, AnomaliesResponse

router = APIRouter(prefix="/anomalies", tags=["anomalies"])

# ── Model paths ──────────────────────────────────────────────────────────────
# CHANGED: old path pointed to models/ids_pipeline.pkl (joblib artifact).
#          New model is a .pt checkpoint produced by torch.save() in the
#          notebook's final cell.  label_mapping.json is a separate file
#          also saved by the notebook; it carries index_to_label and
#          node_names so we do NOT hard-code class names here.
_MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
GNN_MODEL_PATH = _MODELS_DIR / "gnn_model_complete.pt"
LABEL_MAPPING_PATH = _MODELS_DIR / "label_mapping.json"

# ── Module-level singletons (lazy-loaded) ────────────────────────────────────
_gnn_model: Optional["TemporalGAT"] = None
_label_mapping: Optional[Dict] = None
_device: Optional[torch.device] = None

# ── GNN hyper-parameters (must match the saved checkpoint) ──────────────────
# CHANGED: these constants replace TOP_FEATURES and CLASS_NAMES.
#          The GNN notebook fixes node_feature_dim=14 and seq_len=5.
#          num_classes is loaded dynamically from label_mapping.json so it
#          stays in sync if the notebook is retrained with a different label set.
GNN_NODE_FEATURE_DIM = 14   # features per node per time-step
GNN_SEQ_LEN = 5              # temporal window length
GNN_NUM_NODES = 26           # nodes in the network graph (from dataset metadata)

# Severity table — kept compatible with the old API contract so the
# dashboard does not need changes.  Label strings now come from
# label_mapping.json rather than the hard-coded CLASS_NAMES dict.
# CHANGED: keys now match GNN label strings (may differ slightly from old IDS
#          class names).  Add/update entries whenever the notebook is retrained.
ATTACK_SEVERITY: Dict[str, str] = {
    "BENIGN": "Low",
    "Bot": "High",
    "DDoS": "High",
    "DoS GoldenEye": "High",
    "DoS Hulk": "High",
    "DoS Slowhttptest": "Medium",
    "DoS slowloris": "Medium",
    "FTP-Patator": "Medium",
    "Heartbleed": "Critical",
    "Infiltration": "Critical",
    "PortScan": "Medium",
    "SSH-Patator": "Medium",
    "Web Attack - Brute Force": "High",
    "Web Attack - SQL Injection": "Critical",
    "Web Attack - XSS": "High",
    # GNN may also predict these aggregated labels from its richer label set:
    "NetworkScan": "Medium",
    "Reconnaissance": "Medium",
    "Exploit": "High",
    "Malware": "High",
    "C2": "Critical",
    "Exfiltration": "Critical",
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TemporalGAT — inline definition so the route file is self-contained and
# torch.load() can reconstruct the model without importing the notebook.
#
# CHANGED: the old code never needed a model class definition because
#          joblib.load() restores sklearn pipelines transparently.
#          PyTorch's torch.load()/load_state_dict() requires the class to be
#          present in scope at load time.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class TemporalGAT(nn.Module):
    """
    Temporal Graph Attention Network — copied verbatim from gnn_training_notebook.
    CHANGED: this class was absent in the old routes file. It must be defined
             here (or imported from a shared module) so load_state_dict() works.
    """

    def __init__(
        self,
        node_feature_dim: int = 14,
        hidden_dim: int = 128,
        num_classes: int = 21,
        seq_len: int = 5,
        num_gat_layers: int = 3,
        num_heads: int = 4,
        dropout: float = 0.3,
    ):
        super().__init__()

        self.node_feature_dim = node_feature_dim
        self.hidden_dim = hidden_dim
        self.num_classes = num_classes
        self.seq_len = seq_len
        self.dropout = dropout

        # Temporal encoder: bi-directional LSTM over the seq_len dimension
        self.temporal_encoder = nn.LSTM(
            input_size=node_feature_dim,
            hidden_size=hidden_dim // 2,
            num_layers=2,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if seq_len > 1 else 0,
        )

        # Stack of GAT layers
        self.gat_layers = nn.ModuleList()
        self.gat_layers.append(
            GATConv(
                in_channels=hidden_dim,
                out_channels=hidden_dim // num_heads,
                heads=num_heads,
                dropout=dropout,
                concat=True,
            )
        )
        for _ in range(num_gat_layers - 2):
            self.gat_layers.append(
                GATConv(
                    in_channels=hidden_dim,
                    out_channels=hidden_dim // num_heads,
                    heads=num_heads,
                    dropout=dropout,
                    concat=True,
                )
            )
        self.gat_layers.append(
            GATConv(
                in_channels=hidden_dim,
                out_channels=hidden_dim,
                heads=1,
                dropout=dropout,
                concat=False,
            )
        )

        self.layer_norms = nn.ModuleList(
            [nn.LayerNorm(hidden_dim) for _ in range(num_gat_layers)]
        )

        # Node-level classifier
        self.node_classifier = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, num_classes),
        )

        # Graph-level pooling + window classifier
        self.graph_pool = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
        )
        self.window_classifier = nn.Sequential(
            nn.Linear(hidden_dim // 2 + num_classes, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, num_classes),
        )

    def forward(self, data: Data):
        x, edge_index = data.x, data.edge_index
        batch = data.batch if hasattr(data, "batch") and data.batch is not None else None

        if batch is not None:
            return self._forward_batch(data)

        # ── Single-graph forward (inference path used here) ──────────────────
        x_flat = x.view(-1, self.seq_len, self.node_feature_dim)
        lstm_out, _ = self.temporal_encoder(x_flat)
        x_encoded = lstm_out[:, -1, :]  # last time-step hidden state

        h = x_encoded
        for gat, norm in zip(self.gat_layers, self.layer_norms):
            h_new = gat(h, edge_index)
            h_new = F.elu(h_new)
            h_new = norm(h_new)
            h_new = F.dropout(h_new, p=self.dropout, training=self.training)
            h = h + h_new if h.shape == h_new.shape else h_new

        node_logits = self.node_classifier(h)

        h_pooled = self.graph_pool(h)
        h_graph = (torch.max(h_pooled, dim=0)[0] + torch.mean(h_pooled, dim=0)) / 2

        node_probs = F.softmax(node_logits, dim=-1)
        max_node_pred = torch.max(node_probs, dim=0)[0]

        window_input = torch.cat([h_graph, max_node_pred], dim=0).unsqueeze(0)
        window_logits = self.window_classifier(window_input)

        return node_logits, window_logits

    def _forward_batch(self, data: Data):
        """Batched forward — kept for completeness but not used in inference."""
        x, edge_index, batch = data.x, data.edge_index, data.batch
        num_graphs = int(batch.max().item()) + 1
        num_nodes_per_graph = x.shape[0] // num_graphs

        x_reshaped = x.view(
            num_graphs * num_nodes_per_graph, self.seq_len, self.node_feature_dim
        )
        lstm_out, _ = self.temporal_encoder(x_reshaped)
        x_encoded = lstm_out[:, -1, :]

        h = x_encoded
        for gat, norm in zip(self.gat_layers, self.layer_norms):
            h_new = gat(h, edge_index)
            h_new = F.elu(h_new)
            h_new = norm(h_new)
            h_new = F.dropout(h_new, p=self.dropout, training=self.training)
            h = h + h_new if h.shape == h_new.shape else h_new

        node_logits = self.node_classifier(h)
        h_pooled = self.graph_pool(h)

        h_graph_max = torch.zeros(num_graphs, h_pooled.shape[1], device=h.device)
        h_graph_mean = torch.zeros(num_graphs, h_pooled.shape[1], device=h.device)
        for i in range(num_graphs):
            mask = batch == i
            h_graph_max[i] = torch.max(h_pooled[mask], dim=0)[0]
            h_graph_mean[i] = torch.mean(h_pooled[mask], dim=0)

        h_graph = (h_graph_max + h_graph_mean) / 2
        max_node_pred = torch.zeros(num_graphs, self.num_classes, device=h.device)
        for i in range(num_graphs):
            mask = batch == i
            node_probs = F.softmax(node_logits[mask], dim=-1)
            max_node_pred[i] = torch.max(node_probs, dim=0)[0]

        window_input = torch.cat([h_graph, max_node_pred], dim=-1)
        window_logits = self.window_classifier(window_input)
        return node_logits, window_logits


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Model + label-mapping loader
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _get_device() -> torch.device:
    """Return (and cache) the compute device."""
    global _device
    if _device is None:
        _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return _device


def load_label_mapping() -> Dict:
    """
    Load label_mapping.json saved by the notebook.

    CHANGED: old code used a hard-coded CLASS_NAMES dict.
             The GNN notebook writes label_mapping.json containing
             label_to_index and index_to_label; we read it at runtime
             so label changes in future training runs are picked up
             automatically without editing this file.
    """
    global _label_mapping
    if _label_mapping is None:
        if not LABEL_MAPPING_PATH.exists():
            raise FileNotFoundError(
                f"label_mapping.json not found at {LABEL_MAPPING_PATH}. "
                "Run the gnn_training_notebook to regenerate it."
            )
        with open(LABEL_MAPPING_PATH, "r") as f:
            raw = json.load(f)
        # index_to_label keys are strings in JSON; convert to int
        _label_mapping = {
            "label_to_index": raw["label_to_index"],
            "index_to_label": {int(k): v for k, v in raw["index_to_label"].items()},
            "node_names": raw.get("node_names", []),
        }
    return _label_mapping


def load_gnn_model() -> TemporalGAT:
    """
    Lazy-load the TemporalGAT model from the .pt checkpoint.

    CHANGED: old load_model() called joblib.load() on ids_pipeline.pkl and
             handled dict / pipeline variants.
             New loader calls torch.load() on gnn_model_complete.pt, extracts
             the CONFIG dict to reconstruct the exact architecture, then calls
             load_state_dict() to restore weights.
             Running in eval() + no_grad is essential for inference correctness
             (disables dropout and batch-norm training behaviour).
    """
    global _gnn_model
    if _gnn_model is None:
        if not GNN_MODEL_PATH.exists():
            raise FileNotFoundError(
                f"GNN model not found at {GNN_MODEL_PATH}. "
                "Run the gnn_training_notebook to train and save the model."
            )

        device = _get_device()

        # CHANGED: torch.load() replaces joblib.load()
        checkpoint = torch.load(GNN_MODEL_PATH, map_location=device)

        # The notebook saves: model_state_dict, config, history, test_metrics
        config = checkpoint.get("config", {})

        # Load label mapping to get num_classes dynamically
        mapping = load_label_mapping()
        num_classes = len(mapping["label_to_index"])

        # Reconstruct architecture with the exact hyper-params used during training
        # CHANGED: the old pipeline had no architecture to reconstruct — sklearn
        #          pipelines are fully serialised by joblib.
        _gnn_model = TemporalGAT(
            node_feature_dim=GNN_NODE_FEATURE_DIM,
            hidden_dim=config.get("hidden_dim", 128),
            num_classes=num_classes,
            seq_len=config.get("seq_len", GNN_SEQ_LEN),
            num_gat_layers=config.get("num_gat_layers", 3),
            num_heads=config.get("num_heads", 4),
            dropout=config.get("dropout", 0.3),
        ).to(device)

        _gnn_model.load_state_dict(checkpoint["model_state_dict"])
        _gnn_model.eval()  # CHANGED: required — disables dropout at inference time

    return _gnn_model


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Mock graph-snapshot generator
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _build_fully_connected_edge_index(num_nodes: int) -> torch.Tensor:
    """
    Build a fully-connected edge_index for num_nodes nodes.

    CHANGED: the old pipeline had no graph topology concept — it processed
             independent tabular rows.  The GNN requires an edge_index tensor
             of shape [2, num_edges].  When real topology metadata is not
             available at inference time we fall back to a fully-connected
             graph, which mirrors the notebook's own fallback logic in
             NetworkGNNDataset._build_edge_index().
    """
    edges = [
        [i, j]
        for i in range(num_nodes)
        for j in range(num_nodes)
        if i != j
    ]
    return torch.tensor(edges, dtype=torch.long).t().contiguous()


def generate_mock_graph_snapshot(num_nodes: int = GNN_NUM_NODES) -> Data:
    """
    Generate a single synthetic graph snapshot for demo/fallback inference.

    CHANGED: the old generate_mock_network_flows() produced a pandas DataFrame
             with 50 named tabular features per flow (one row = one sample).
             The GNN operates on graph Data objects where:
               x            : [num_nodes, seq_len, node_feature_dim] float tensor
               edge_index   : [2, num_edges] long tensor
             No pandas or sklearn feature selection is needed.
    """
    np.random.seed(42)

    # Simulate node features across seq_len time-steps
    # Each of the 14 features represents a per-node network metric
    # (e.g. byte rates, packet counts, connection state flags aggregated per node)
    node_features = torch.tensor(
        np.random.randn(num_nodes, GNN_SEQ_LEN, GNN_NODE_FEATURE_DIM).astype(np.float32)
    )

    edge_index = _build_fully_connected_edge_index(num_nodes)

    return Data(x=node_features, edge_index=edge_index)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GNN inference
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def predict_with_gnn(graph_data: Data) -> List[Tuple[int, str, float]]:
    """
    Run a graph snapshot through TemporalGAT and return per-node predictions.

    Returns a list of (class_index, class_name, confidence) tuples,
    one entry per node in the graph.

    CHANGED: old predict_anomalies() called model.predict(X) and
             model.predict_proba(X) — the sklearn API.
             The GNN forward() returns (node_logits, window_logits) tensors.
             We apply softmax to node_logits to get per-node class probabilities,
             then argmax for the predicted class.
             window_logits gives a single window-level prediction which is also
             surfaced (see generate_anomalies_from_gnn()).
    """
    model = load_gnn_model()
    mapping = load_label_mapping()
    index_to_label: Dict[int, str] = mapping["index_to_label"]
    device = _get_device()

    graph_data = graph_data.to(device)

    # CHANGED: torch.no_grad() replaces the bare try/except around predict_proba.
    #          It is mandatory to avoid computing unnecessary gradients.
    with torch.no_grad():
        node_logits, _window_logits = model(graph_data)

    # Per-node probabilities: [num_nodes, num_classes]
    node_probs = F.softmax(node_logits, dim=-1).cpu().numpy()

    results: List[Tuple[int, str, float]] = []
    for probs in node_probs:
        pred_idx = int(np.argmax(probs))
        confidence = float(np.max(probs))
        label = index_to_label.get(pred_idx, f"Class_{pred_idx}")
        results.append((pred_idx, label, confidence))

    return results


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Anomaly generation from GNN predictions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def generate_anomalies_from_gnn() -> List[AnomalyItem]:
    """
    Run mock graph data through the GNN and convert node predictions to AnomalyItems.

    CHANGED: replaces generate_anomalies_from_predictions().
             Key differences:
               - Input is a graph Data object, not a pandas DataFrame
               - Predictions are per-node (one entry per network node),
                 not per flow-row
               - source_ip is mapped from the node_names list in label_mapping
                 when available, making IPs more semantically meaningful
               - The AnomalyItem schema and returned JSON structure are
                 UNCHANGED so the dashboard requires no modifications.
    """
    graph_snapshot = generate_mock_graph_snapshot()

    # CHANGED: call predict_with_gnn() instead of predict_anomalies()
    predictions = predict_with_gnn(graph_snapshot)

    # Optionally use node_names for IP labelling
    mapping = load_label_mapping()
    node_names: List[str] = mapping.get("node_names", [])

    anomalies: List[AnomalyItem] = []
    base_time = datetime.now()

    for node_idx, (pred_class, class_name, confidence) in enumerate(predictions):
        # Skip benign nodes — same logic as the old implementation
        if class_name.upper() == "BENIGN":
            continue

        # Use node name as source IP hint when available
        # CHANGED: old code used purely random IPs; now we reflect the node
        #          identity from the graph topology when metadata is present.
        if node_idx < len(node_names):
            # node_names are identifiers like "router-1" or "192.168.x.x"
            raw_name = node_names[node_idx]
            source_ip = raw_name if _looks_like_ip(raw_name) else _node_name_to_ip(raw_name, node_idx)
        else:
            source_ip = (
                f"{random.randint(1, 223)}.{random.randint(0, 255)}"
                f".{random.randint(0, 255)}.{random.randint(1, 254)}"
            )

        dest_ip = f"192.168.{random.randint(0, 255)}.{random.randint(1, 254)}"

        severity = ATTACK_SEVERITY.get(class_name, "Medium")
        timestamp = (base_time - timedelta(minutes=random.randint(1, 120))).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # CHANGED: status logic is identical to the old implementation —
        #          kept intentionally for dashboard compatibility.
        status = (
            "Ongoing" if confidence > 0.9
            else "Resolved" if confidence < 0.7
            else "Investigating"
        )

        anomalies.append(
            AnomalyItem(
                id=str(node_idx + 1),
                timestamp=timestamp,
                source_ip=source_ip,
                dest_ip=dest_ip,
                threat_type=class_name,
                severity=severity,
                status=status,
            )
        )

    # Fallback: if GNN predicts all nodes benign, return demo items
    # CHANGED: same fallback philosophy as the old code; kept for resilience.
    if not anomalies:
        anomalies = [
            AnomalyItem(
                id="1",
                timestamp=(base_time - timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S"),
                source_ip="203.0.113.45",
                dest_ip="192.168.1.100",
                threat_type="PortScan",
                severity="Medium",
                status="Ongoing",
            ),
            AnomalyItem(
                id="2",
                timestamp=(base_time - timedelta(minutes=45)).strftime("%Y-%m-%d %H:%M:%S"),
                source_ip="198.51.100.22",
                dest_ip="192.168.1.50",
                threat_type="DoS Hulk",
                severity="High",
                status="Resolved",
            ),
        ]

    return anomalies


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Small helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _looks_like_ip(s: str) -> bool:
    """Return True if s looks like an IPv4 address."""
    parts = s.split(".")
    if len(parts) != 4:
        return False
    return all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)


def _node_name_to_ip(name: str, fallback_idx: int) -> str:
    """
    Derive a deterministic fake IP from a node name string.
    CHANGED: new helper — needed because GNN node identities are named
             network entities rather than anonymous flow rows.
    """
    h = hash(name) % (255 * 255)
    return f"10.{(h >> 8) & 0xFF}.{h & 0xFF}.{(fallback_idx % 254) + 1}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Filtering — UNCHANGED from original
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def filter_anomalies(
    anomalies: List[AnomalyItem],
    search: Optional[str],
    severity: Optional[str],
) -> List[AnomalyItem]:
    """Filter anomalies by search string and severity. Logic unchanged."""
    filtered = anomalies

    if search:
        search_lower = search.lower()
        filtered = [
            a for a in filtered
            if search in a.source_ip
            or search in a.dest_ip
            or search_lower in a.threat_type.lower()
        ]

    if severity and severity != "all":
        filtered = [a for a in filtered if a.severity == severity]

    return filtered


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FastAPI route — signature and response model UNCHANGED
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("", response_model=AnomaliesResponse)
async def read_anomalies(
    search: Optional[str] = Query(None, description="Search by IP or threat type"),
    severity: Optional[str] = Query(
        None, description="Filter by severity: High, Medium, Low, Critical, or all"
    ),
):
    """
    Return detected network anomalies.

    CHANGED: internally calls generate_anomalies_from_gnn() instead of
             generate_anomalies_from_predictions().
             The route path, query parameters, and AnomaliesResponse schema
             are all unchanged so the dashboard frontend requires zero changes.
    """
    # CHANGED: migrated from old anomaly model to gnn_training_notebook
    all_anomalies = generate_anomalies_from_gnn()
    filtered = filter_anomalies(all_anomalies, search, severity)
    return AnomaliesResponse(anomalies=filtered, total=len(filtered))