# RetailPulse AI — Deployment Guide

This guide covers deploying RetailPulse AI to **Google Cloud Run** — the recommended
hosting approach for the hackathon submission (satisfies the "hosted project URL" requirement).

---

## Option A: Google Cloud Run (Recommended for Submission)

### Prerequisites
- [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) installed and authenticated
- A Google Cloud project with billing enabled
- MongoDB Atlas cluster (free tier M0 works)
- Gemini API key or Vertex AI enabled on your project

### 1. Set your project

```bash
export PROJECT_ID=your-gcp-project-id
export REGION=us-central1
gcloud config set project $PROJECT_ID
```

### 2. Enable required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com
```

### 3. Store secrets in Secret Manager

```bash
# Store your MongoDB URI
echo -n "mongodb+srv://user:pass@cluster.mongodb.net/retailpulse" | \
  gcloud secrets create MONGODB_URI --data-file=-

# Store your Gemini API key
echo -n "your_gemini_api_key" | \
  gcloud secrets create GOOGLE_API_KEY --data-file=-
```

### 4. Build and push the container

```bash
# Build
gcloud builds submit --tag gcr.io/$PROJECT_ID/retailpulse-ai

# Or use Artifact Registry (recommended)
gcloud artifacts repositories create retailpulse \
  --repository-format=docker \
  --location=$REGION

docker build -t $REGION-docker.pkg.dev/$PROJECT_ID/retailpulse/app:latest .
docker push $REGION-docker.pkg.dev/$PROJECT_ID/retailpulse/app:latest
```

### 5. Deploy to Cloud Run

```bash
gcloud run deploy retailpulse-ai \
  --image $REGION-docker.pkg.dev/$PROJECT_ID/retailpulse/app:latest \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --port 7860 \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --set-secrets "MONGODB_URI=MONGODB_URI:latest,GOOGLE_API_KEY=GOOGLE_API_KEY:latest" \
  --set-env-vars "MALL_NAME=Sunrise Mall,AGENT_MODEL=gemini-2.5-flash,UI_PORT=7860"
```

### 6. Get your hosted URL

```bash
gcloud run services describe retailpulse-ai \
  --region $REGION \
  --format "value(status.url)"
```

This URL is what you submit as the "hosted project URL" on Devpost.

---

## Option B: Local Development with Docker Compose

The fastest way to run everything locally for development and demo recording.

```bash
# 1. Copy and fill in your credentials
cp .env.example .env

# 2. Start MongoDB + seed data + web UI
docker compose up --build

# 3. Open http://localhost:7860
```

The `seed` service runs automatically and populates MongoDB with 90 days of
realistic demo data before the app starts.

---

## Option C: Local Python (No Docker)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Make sure Node.js 18+ is installed (for MongoDB MCP Server)
node --version

# 3. Configure environment
cp .env.example .env
# Edit .env with your MONGODB_URI and GOOGLE_API_KEY

# 4. Start local MongoDB (if not using Atlas)
docker run -d -p 27017:27017 --name mongo mongo:7

# 5. Seed demo data
python scripts/seed_data.py

# 6. Run the web UI
python app.py
# Open http://localhost:7860

# OR run the CLI
python -m retailpulse
```

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `MONGODB_URI` | ✅ | MongoDB connection string |
| `GOOGLE_API_KEY` | ✅ (or Vertex AI) | Gemini API key |
| `GOOGLE_CLOUD_PROJECT` | For Vertex AI | GCP project ID |
| `GOOGLE_CLOUD_LOCATION` | For Vertex AI | Region (e.g. us-central1) |
| `AGENT_MODEL` | Optional | Model name (default: gemini-2.5-flash) |
| `MALL_NAME` | Optional | Mall name shown in UI (default: Sunrise Mall) |
| `UI_PORT` | Optional | Web UI port (default: 7860) |
| `MDB_ATLAS_CLIENT_ID` | Optional | Atlas API client ID (for Atlas tools) |
| `MDB_ATLAS_CLIENT_SECRET` | Optional | Atlas API client secret |
| `DEBUG` | Optional | Enable debug logging (true/false) |

---

## MongoDB Atlas Setup (Free Tier)

1. Create a free account at [mongodb.com/atlas](https://www.mongodb.com/atlas)
2. Create a free M0 cluster
3. Under **Database Access**, create a user with read/write permissions
4. Under **Network Access**, add `0.0.0.0/0` (allow all IPs) for Cloud Run
5. Get your connection string from **Connect > Drivers**
6. Run `python scripts/seed_data.py` to populate demo data

---

## Hackathon Submission Checklist

- [ ] App deployed and accessible at a public URL
- [ ] GitHub repository is public with Apache 2.0 license visible in About section
- [ ] `README.md` explains the project clearly
- [ ] Demo video (~3 minutes) recorded showing multi-step agent interactions
- [ ] Devpost submission form completed with MongoDB partner track selected
