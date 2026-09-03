# AI-Based Early Warning & Landslide Risk Monitoring System — NER, India

> Decision-support and early-warning platform for landslide risk reduction in the North Eastern Region of India.

## Positioning

This platform is an **analytical/evidence layer that complements official agencies** (e.g., NDMA SACHET-style dissemination). It is **not** a replacement for, or a competing authority to, government warning systems. Every model output retains a visible distinction between (a) model probability, (b) confidence/data-quality, and (c) the final decision, which belongs to an authorized disaster-management workflow.

## Architecture

Six-layer architecture (each independently testable):

| # | Module | Function |
|---|--------|----------|
| 1 | Data Ingestion | Collect weather, satellite, terrain, historical, sensor data |
| 2 | Data Quality | Detect missing, stale, inconsistent values |
| 3 | Susceptibility Model | Baseline propensity of slope failure |
| 4 | Dynamic Prediction | Near-term landslide probability (6h/24h/72h) |
| 5 | Risk Engine | Hazard × Exposure → 0–100 risk score |
| 6 | GIS Dashboard | Interactive map + site detail views |

Plus: Alert Engine (candidate generation for authority review) and Audit & Feedback layer.

## Three-Tier Concept Hierarchy

| Layer | Question | Inputs |
|-------|----------|--------|
| **Susceptibility** | Where is failure structurally more likely? | Slope, geology, soil, elevation, land cover, drainage |
| **Hazard** | Where/when is it likely under current conditions? | Susceptibility + rainfall + soil moisture + deformation |
| **Risk** | What's the consequence if it occurs? | Hazard + exposed population + infrastructure |

## Tech Stack

- **Frontend:** Next.js + React + TypeScript + Tailwind CSS + Leaflet/Mapbox
- **Backend:** Python + FastAPI
- **ML/AI:** scikit-learn, XGBoost/LightGBM, SHAP
- **Database:** PostgreSQL + PostGIS
- **Data Quality:** Scheduled Python jobs

## Data Provenance Tags

Every value shown in the UI carries one of: `Observed | Forecast | Estimated | Interpolated | Model-derived | Simulated (Demo)`

## Getting Started

```bash
# Backend
pip install -r requirements.txt
cd api && uvicorn main:app --reload

# Frontend
cd dashboard && npm install && npm run dev
```

## Limitations

- Model probability ≠ certainty — every risk score must be interpreted with its confidence indicator
- Sparse high-elevation rainfall observations across NER
- Limited geotechnical data availability
- Communication gaps and false alarms are tracked operational risks
- Sensor and connectivity outages in remote terrain (mitigated by store-and-forward design)
- Incomplete/uneven historical event records

## Future Scope (not in MVP)

- Real IoT hardware deployment at prioritized critical slopes
- InSAR-based wide-area deformation monitoring
- Deep sequence models (LSTM/temporal-CNN)
- Formal integration with NDMA SACHET
- Digital-twin scenario simulation
- Full NER region-wide coverage

## License

Research prototype — not for operational deployment without authority validation.
