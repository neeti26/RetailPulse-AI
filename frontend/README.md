# Frontend

The RetailPulse AI frontend is a **Gradio 6** web application (`app.py` in root).

## Structure

```
frontend/
└── README.md          ← This file (frontend docs)

app.py                 ← Main Gradio app (root level, Cloud Run entry point)
retailpulse/
└── dashboard.py       ← Data layer (MongoDB → Plotly charts)
```

## Tabs

| Tab | Purpose |
|-----|---------|
| 📊 Overview | Live KPI cards, 30-day revenue trend, hourly footfall, category/zone charts |
| 📈 Analytics | Category trend lines, footfall heatmap (zone×hour), underperformers table |
| ⚙️ Operations | Open alerts, active promotions, lease expiry tracker |
| 🤖 AI Assistant | Chat with Gemini 2.5 Flash + 8 quick-action buttons |

## Running Locally

```bash
python app.py
# Opens at http://localhost:8080
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `MONGODB_URI` | ✅ | Atlas connection string |
| `GOOGLE_API_KEY` | ✅ | Gemini API key |
| `MALL_NAME` | Optional | Display name (default: Sunrise Mall) |
| `PORT` | Optional | Server port (default: 8080, set by Cloud Run) |
