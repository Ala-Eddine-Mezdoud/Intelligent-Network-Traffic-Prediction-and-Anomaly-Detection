# Setup Guide

This guide explains how to run the Network Traffic Prediction & Anomaly Detection system.

## Prerequisites

- Python 3.10+ with Anaconda/conda
- Node.js 18+ with npm/pnpm
- Git

---

## Backend (FastAPI)

The backend provides ML-powered APIs for traffic forecasting and anomaly detection.

### 1. Navigate to the API directory

```bash
cd models_api
```

### 2. Activate the conda environment

```bash
conda activate network-traffic-prediction-env
```

### 3. Install dependencies (if not already installed)

```bash
pip install -r requirements.txt
```

### 4. Start the development server

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

### API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health check: `http://localhost:8000/health`

---

## Frontend (Next.js Dashboard)

The dashboard provides real-time visualization of network metrics, predictions, and alerts.

### 1. Navigate to the dashboard directory

```bash
cd network-monitoring-dashboard
```

### 2. Install dependencies (if not already installed)

```bash
npm install
# or
pnpm install
```

### 3. Start the development server

```bash
npm run dev
# or
pnpm dev
```

The dashboard will be available at `http://localhost:3000`

---

## Running Both Services

For full functionality, run both services simultaneously:

**Terminal 1 (Backend):**
```bash
cd models_api
conda activate network-traffic-prediction-env
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 (Frontend):**
```bash
cd network-monitoring-dashboard
npm run dev
```

---

## Environment Variables

Create a `.env` file in `network-monitoring-dashboard` if you need to customize the API URL:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Default is `http://localhost:8000` if not specified.

---

## Troubleshooting

### Backend Issues

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Ensure conda environment is activated and run `pip install -r requirements.txt` |
| Port 8000 in use | Use a different port: `uvicorn app.main:app --reload --port 8001` |
| Model loading errors | Verify `.pkl` files exist in `models_api/models/` directory |

### Frontend Issues

| Issue | Solution |
|-------|----------|
| API connection errors | Ensure backend is running on port 8000 |
| `npm install` fails | Delete `node_modules` and lock files, then reinstall |
| Port 3000 in use | Next.js will automatically use next available port |

---

## Project Structure

```
.
├── models_api/              # FastAPI backend
│   ├── app/
│   │   ├── api/            # API routes
│   │   ├── schemas/        # Pydantic models
│   │   └── main.py         # Application entry point
│   ├── models/             # ML model files (.pkl)
│   └── requirements.txt
│
└── network-monitoring-dashboard/  # Next.js frontend
    ├── app/                # Next.js app routes
    ├── components/         # React components
    ├── lib/                # API client and utilities
    └── package.json
```
