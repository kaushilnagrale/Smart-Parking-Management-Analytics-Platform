# 🅿️ Smart Parking Management & Analytics Platform

A full-stack intelligent parking management system that integrates **computer vision**, **real-time APIs**, and **cloud analytics** to monitor parking utilization and optimize space allocation.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![React](https://img.shields.io/badge/React-18-61DAFB)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688)
![TensorFlow](https://img.shields.io/badge/TensorFlow-2.15-FF6F00)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    React + Tailwind                      │
│              (Admin Dashboard & Live View)                │
└─────────────┬───────────────────────────┬───────────────┘
              │ REST API                  │ WebSocket
┌─────────────▼───────────────────────────▼───────────────┐
│                   FastAPI Backend                         │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐     │
│  │ Auth &   │  │ Parking  │  │  Analytics Engine   │     │
│  │ RBAC     │  │ Manager  │  │  (Synapse/Pandas)   │     │
│  └──────────┘  └──────────┘  └────────────────────┘     │
│  ┌──────────────────────────────────────────────────┐   │
│  │         ML Pipeline (OpenCV + TensorFlow)         │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌─────────┐ │   │
│  │  │ Vehicle     │  │ License Plate │  │ Occupancy│ │   │
│  │  │ Detection   │  │ Recognition   │  │ Counting │ │   │
│  │  │ (YOLOv8)    │  │ (Tesseract)   │  │          │ │   │
│  │  └─────────────┘  └──────────────┘  └─────────┘ │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────┬───────────────────────────┬───────────────┘
              │                           │
┌─────────────▼──────────┐  ┌─────────────▼──────────────┐
│   PostgreSQL           │  │   Neo4j (Graph DB)          │
│   - Users & Roles      │  │   - Zone Relationships      │
│   - Parking Events     │  │   - Spatial Queries          │
│   - Analytics Data     │  │   - Route Optimization       │
└────────────────────────┘  └────────────────────────────┘
              │
┌─────────────▼──────────────────────────────────────────┐
│              Azure Cloud Services                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Azure Data   │  │ Azure Synapse │  │ Azure Blob   │ │
│  │ Factory      │  │ Analytics     │  │ Storage      │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## 🚀 Features

- **Live Camera Feed Processing** — Real-time video streams analyzed by CV pipeline
- **Vehicle Detection** — YOLOv8-based object detection for cars, trucks, motorcycles
- **License Plate Recognition** — OpenCV preprocessing + Tesseract OCR
- **Real-Time Occupancy** — Per-zone vehicle counting with WebSocket updates
- **Admin Dashboard** — Utilization trends, heatmaps, peak-hour analytics
- **REST APIs** — Full CRUD for zones, events, availability queries
- **Role-Based Access Control** — Admin, Operator, Viewer roles with JWT auth
- **Cloud ETL Pipeline** — Azure Data Factory for historical data processing
- **Graph-Based Zone Mapping** — Neo4j for spatial relationships and routing

## 📁 Project Structure

```
smart-parking-platform/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI route handlers
│   │   ├── core/           # Config, security, database
│   │   ├── ml/             # CV & ML pipeline modules
│   │   ├── models/         # SQLAlchemy & Neo4j models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic layer
│   │   └── utils/          # Helpers & utilities
│   ├── tests/              # Pytest test suite
│   ├── main.py             # FastAPI application entry
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── hooks/          # Custom React hooks
│   │   ├── services/       # API client & WebSocket
│   │   ├── pages/          # Route-level pages
│   │   └── utils/          # Frontend helpers
│   ├── package.json
│   └── tailwind.config.js
├── ml/
│   ├── models/             # Trained model weights
│   ├── scripts/            # Training & evaluation
│   └── data/               # Sample datasets
├── infra/
│   ├── docker/             # Dockerfiles
│   └── azure/              # ARM templates & ADF pipelines
├── docs/                   # Documentation
└── docker-compose.yml
```

## ⚡ Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 18+
- Python 3.11+
- PostgreSQL 16
- Neo4j 5.x (optional, for graph features)

### 1. Clone & Setup Environment

```bash
git clone https://github.com/yourusername/smart-parking-platform.git
cd smart-parking-platform
cp .env.example .env
# Edit .env with your configurations
```

### 2. Start with Docker Compose

```bash
docker-compose up --build
```

### 3. Manual Setup (Development)

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### 4. Access

- **Frontend Dashboard:** http://localhost:5173
- **API Docs (Swagger):** http://localhost:8000/docs
- **API Docs (ReDoc):** http://localhost:8000/redoc

### Default Credentials
```
Admin:    admin@smartparking.com / admin123
Operator: operator@smartparking.com / operator123
Viewer:   viewer@smartparking.com / viewer123
```

## 📊 Data Science Theory Used

See [docs/DATA_SCIENCE_THEORY.md](DATA_SCIENCE_THEORY.md) for comprehensive coverage.

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
