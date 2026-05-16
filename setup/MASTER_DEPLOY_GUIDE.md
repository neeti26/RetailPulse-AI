# RetailPulse AI — Master Deployment Guide
# Complete this in order. Each step has exact commands.

---

## ✅ CHECKLIST

- [ ] Step 1: Get a Gemini API key
- [ ] Step 2: Set up MongoDB Atlas + seed data
- [ ] Step 3: Install Google Cloud CLI
- [ ] Step 4: Deploy to Cloud Run (primary URL)
- [ ] Step 5: Deploy to Hugging Face Spaces (backup URL)
- [ ] Step 6: Verify both URLs work
- [ ] Step 7: Submit to Devpost

---

## STEP 1 — Get a Gemini API Key (5 minutes)

1. Go to https://aistudio.google.com/app/apikey
2. Click **"Create API key"**
3. Copy it — looks like `AIzaSy...`
4. Save it somewhere safe

---

## STEP 2 — MongoDB Atlas (10 minutes)

Follow `setup/3_mongodb_atlas_setup.md` in full.

At the end you'll have:
- `MONGODB_URI=mongodb+srv://retailpulse:PASSWORD@cluster.mongodb.net/retailpulse`
- Demo data seeded (20 tenants, 90 days of history)

---

## STEP 3 — Install Google Cloud CLI (5 minutes)

Follow `setup/1_install_gcloud.md`.

Then run:
```powershell
gcloud init
gcloud auth login
gcloud auth application-default login
```

Create a Google Cloud project at https://console.cloud.google.com if you don't have one.
Note your **Project ID** (e.g. `my-project-123456`).

---

## STEP 4 — Deploy to Cloud Run (10 minutes)

Open PowerShell in the project folder and run:

```powershell
.\setup\2_gcloud_setup.ps1 `
  -ProjectId "YOUR_GCP_PROJECT_ID" `
  -MongoUri "mongodb+srv://retailpulse:PASSWORD@cluster.mongodb.net/retailpulse" `
  -GeminiKey "AIzaSy..."
```

At the end you'll see:
```
✅ DEPLOYMENT COMPLETE!
🌐 Live URL : https://retailpulse-ai-xxxxxxxx-uc.a.run.app
```

**Copy that URL — it goes on Devpost as your hosted project link.**

---

## STEP 5 — Deploy to Hugging Face Spaces (10 minutes)

Follow `setup/4_huggingface_setup.md`.

Quick version:
```bash
git remote add huggingface https://huggingface.co/spaces/YOUR_HF_USERNAME/RetailPulse-AI
git push huggingface main
```

Add your secrets in the Space settings UI.

Your backup URL: `https://YOUR_HF_USERNAME-retailpulse-ai.hf.space`

---

## STEP 6 — Verify Both URLs

Open both URLs and:
1. Click **"🔄 Refresh Dashboard"** — KPI cards should show data
2. Click **"🚨 Anomaly Scan"** — agent should respond with findings
3. Click **"📊 Weekly Report"** — agent should generate and save a report

If the dashboard shows zeros but chat works, the MongoDB URI is wrong.
If chat gives an API error, the Gemini key is wrong.

---

## STEP 7 — Devpost Submission

Fill in:
- **Project name**: RetailPulse AI
- **Elevator pitch**: An autonomous mall intelligence agent that detects anomalies, plans promotions, and generates reports — powered by Google ADK, Gemini, and MongoDB.
- **Try it out links**:
  - Cloud Run URL (primary)
  - HuggingFace Space URL (backup)
  - GitHub: https://github.com/neeti26/RetailPulse-AI
- **Track**: MongoDB Partner Track
- **Demo video**: Record using `DEMO_SCRIPT.md`, upload to YouTube (unlisted), paste link

---

## Troubleshooting

**Cloud Run: "Container failed to start"**
```bash
gcloud run services logs read retailpulse-ai --region=us-central1 --limit=50
```
Usually means MONGODB_URI or GOOGLE_API_KEY secret is wrong.

**MongoDB: "Authentication failed"**
- Check the password has no special characters that need URL-encoding
- `@` → `%40`, `#` → `%23`, `$` → `%24`

**HuggingFace: App crashes on startup**
- Check Space logs (Logs tab in the Space)
- Make sure all 3 secrets are set: MONGODB_URI, GOOGLE_API_KEY, MALL_NAME

**Gradio: "No response received"**
- The agent timed out — complex queries can take 30-60s
- Increase Cloud Run timeout: add `--timeout=600` to the deploy command
