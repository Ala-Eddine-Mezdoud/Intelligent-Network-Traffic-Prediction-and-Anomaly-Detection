# GNN Training for Network Anomaly Prediction

This directory contains the training pipeline for Graph Neural Networks that predict network anomalies from telemetry snapshots.

## Quick Start

### 1. Install Dependencies

```bash
cd /Users/alaeddine/dev/Intelligent-Network-Traffic-Prediction-and-Anomaly-Detection/ml_training

# Install PyTorch and PyTorch Geometric
pip install torch torchvision torchaudio
pip install torch-geometric torch-scatter torch-sparse

# Or install all requirements
pip install -r requirements.txt
```

### 2. Train a Model

```bash
# Train Temporal GAT model on 30-second horizon
python train_gnn.py \
    --data_dir data/gnn_datasets/gnn_20260501_223419 \
    --horizon horizon_30s \
    --model_type temporal_gat \
    --seq_len 5 \
    --epochs 100 \
    --batch_size 4 \
    --hidden_dim 128 \
    --use_class_weights
```

### 3. Run Inference

```bash
# Evaluate trained model
python inference_gnn.py \
    --model_path models/gnn/temporal_gat_horizon_30s_*/checkpoint_best.pt \
    --data_dir data/gnn_datasets/gnn_20260501_223419 \
    --mode batch \
    --detailed_report

# Single window prediction
python inference_gnn.py \
    --model_path models/gnn/temporal_gat_horizon_30s_*/checkpoint_best.pt \
    --data_dir data/gnn_datasets/gnn_20260501_223419 \
    --mode single \
    --window_idx 10
```

## Files Overview

| File | Description |
|------|-------------|
| `gnn_dataset.py` | PyTorch Geometric dataset loader for JSON snapshots |
| `gnn_model.py` | Temporal GAT and Simple GAT model architectures |
| `train_gnn.py` | Training script with train/val/test splits |
| `inference_gnn.py` | Inference script for batch/streaming/single modes |
| `requirements.txt` | Python dependencies |

## Model Architecture

### TemporalGAT

The `TemporalGAT` model combines:

1. **Temporal Encoding**: Bidirectional LSTM processes sequential node features
2. **Graph Attention**: Multi-head GAT layers aggregate spatial information
3. **Multi-task Heads**: 
   - Node-level classification (per-node anomaly detection)
   - Window-level classification (global anomaly state)

### Input Format

- **Node Features**: 26 nodes × 14 features per node
  - Traffic metrics (bytes, packets, drops)
  - Latency/jitter
  - Connection state
  - Queue/network emulation state
  
- **Edge Features**: Topology connectivity with 6 features per edge
  - Link utilization
  - Protocol breakdown
  
- **Sequence Length**: 5 consecutive time windows (configurable)

### Output Format

- **Node Predictions**: Per-node anomaly class (21 classes)
- **Window Prediction**: Global network state (21 classes)
- **Predictive Horizons**: 15s, 30s, or 60s look-ahead

## Training Options

### Command Line Arguments

```bash
python train_gnn.py \
    --data_dir PATH              # Dataset directory
    --horizon horizon_30s        # 15s, 30s, or 60s
    --model_type temporal_gat    # temporal_gat or simple_gat
    --seq_len 5                  # Sequence length
    --epochs 100                 # Training epochs
    --batch_size 4               # Keep small for graphs
    --lr 0.001                   # Learning rate
    --hidden_dim 128             # Hidden dimension
    --num_gat_layers 3           # GAT layers
    --num_heads 4                # Attention heads
    --dropout 0.3                # Dropout rate
    --use_class_weights          # Handle class imbalance
    --node_loss_weight 1.0       # Node task weight
    --window_loss_weight 0.5     # Window task weight
    --output_dir models/gnn      # Output directory
```

### Model Types

- **temporal_gat**: Uses LSTM + GAT (recommended for sequences)
- **simple_gat**: GAT only (faster, good for single snapshots)

### Prediction Horizons

| Horizon | Description |
|---------|-------------|
| `horizon_15s` | Predict 15 seconds ahead |
| `horizon_30s` | Predict 30 seconds ahead |
| `horizon_60s` | Predict 60 seconds ahead |

## Inference Modes

### Batch Mode

Evaluate on entire dataset and generate metrics:

```bash
python inference_gnn.py \
    --model_path MODEL.pt \
    --data_dir DATA_DIR \
    --mode batch \
    --detailed_report \
    --save_predictions \
    --output predictions.json
```

### Single Mode

Predict for a specific window:

```bash
python inference_gnn.py \
    --model_path MODEL.pt \
    --data_dir DATA_DIR \
    --mode single \
    --window_idx 42
```

### Stream Mode

Simulate real-time streaming inference:

```bash
python inference_gnn.py \
    --model_path MODEL.pt \
    --data_dir DATA_DIR \
    --mode stream \
    --save_predictions \
    --output stream_predictions.json
```

## Output Structure

### Training Output

Models are saved to `models/gnn/{exp_name}/`:

```
models/gnn/temporal_gat_horizon_30s_20260105_143022/
├── checkpoint_best.pt      # Best validation model
├── checkpoint_latest.pt    # Most recent epoch
├── checkpoint_epoch_*.pt   # Periodic checkpoints
├── config.json             # Training configuration
└── results.json            # Training metrics & history
```

### Inference Output

Predictions are saved as JSON:

```json
{
  "window_idx": 10,
  "window_prediction": {
    "label": "DDOS_BUILDUP",
    "confidence": 0.89,
    "top_k": [...]
  },
  "node_predictions": [
    {
      "node_name": "dc_web",
      "predicted_label": "DDOS_TARGET",
      "confidence": 0.95,
      "top_k": [...]
    }
  ],
  "anomaly_detected": true,
  "affected_nodes": ["dc_web", "h1_iot", "h2_cam"]
}
```

## Tips for Best Results

1. **Class Imbalance**: Always use `--use_class_weights` - the dataset has many more NORMAL samples than anomalies

2. **Batch Size**: Keep small (2-8) due to graph structure complexity

3. **Sequence Length**: 3-7 windows typically works best. Too long dilutes signal, too short misses patterns

4. **Hidden Dimension**: 64-256 depending on your GPU memory

5. **Learning Rate**: Start with 0.001, reduce if training is unstable

6. **Overfitting**: Increase `--dropout` if validation loss plateaus while training loss drops

## Troubleshooting

### CUDA Out of Memory

- Reduce `--batch_size` (try 2 or 1)
- Reduce `--hidden_dim` (try 64)
- Reduce `--seq_len` (try 3)
- Use `--model_type simple_gat` (no LSTM, less memory)

### Poor Performance on Rare Classes

- Ensure `--use_class_weights` is enabled
- Try focal loss (modify `train_gnn.py`)
- Collect more data with rare anomaly types

### Slow Training

- Set `--num_workers 4` for faster data loading
- Use `--epochs 50` for quick experiments
- Try `--model_type simple_gat` for faster iterations

## Next Steps

After training:

1. **Export to ONNX/TorchScript** for deployment
2. **Integrate with API** for real-time inference
3. **Add attention visualization** to understand model decisions
4. **Ensemble models** trained on different horizons
