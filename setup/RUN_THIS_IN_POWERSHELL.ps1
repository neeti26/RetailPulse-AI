# ============================================================
# RetailPulse AI — Full Cloud Run Deployment
# INSTRUCTIONS:
# 1. Open Windows PowerShell
# 2. cd "C:\Users\neeti\Desktop\Google Hacakthon"
# 3. & .\setup\RUN_THIS_IN_POWERSHELL.ps1
# ============================================================

$ErrorActionPreference = "Continue"
Set-Location "C:\Users\neeti\Desktop\Google Hacakthon"

$PROJECT  = "gen-lang-client-0047156954"
$REGION   = "us-central1"
$SERVICE  = "retailpulse-ai"
$REPO     = "retailpulse"
$MONGO    = "mongodb+srv://retailpulse:kO9ZqcXf9GfEjhAt@retailpulse-cluster.vr4ivqg.mongodb.net/retailpulse"
$GEMINI   = "AIzaSyCnT6mtPfzDm2vk_B8qx3Awk7f-X7LLo3U"

# Use timestamp tag to force fresh build every time
$TAG      = Get-Date -Format "yyyyMMddHHmmss"
$IMAGE    = "$REGION-docker.pkg.dev/$PROJECT/$REPO/$SERVICE`:$TAG"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host " RetailPulse AI — Cloud Run Deployment" -ForegroundColor Cyan
Write-Host " Image tag: $TAG" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Step 1 — Enable APIs
Write-Host "[1/6] Enabling APIs..." -ForegroundColor Yellow
gcloud services enable run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com cloudbuild.googleapis.com --project=$PROJECT
Write-Host "      Done`n" -ForegroundColor Green

# Step 2 — Create Artifact Registry repo
Write-Host "[2/6] Creating Artifact Registry repo..." -ForegroundColor Yellow
gcloud artifacts repositories create $REPO --repository-format=docker --location=$REGION --project=$PROJECT 2>$null
Write-Host "      Done`n" -ForegroundColor Green

# Step 3 — Store secrets
Write-Host "[3/6] Storing secrets..." -ForegroundColor Yellow
$tmpM = [System.IO.Path]::GetTempFileName()
$tmpG = [System.IO.Path]::GetTempFileName()
[System.IO.File]::WriteAllText($tmpM, $MONGO,  [System.Text.Encoding]::UTF8)
[System.IO.File]::WriteAllText($tmpG, $GEMINI, [System.Text.Encoding]::UTF8)
gcloud secrets create MONGODB_URI    --data-file=$tmpM --project=$PROJECT 2>$null
gcloud secrets versions add MONGODB_URI    --data-file=$tmpM --project=$PROJECT 2>$null
gcloud secrets create GOOGLE_API_KEY --data-file=$tmpG --project=$PROJECT 2>$null
gcloud secrets versions add GOOGLE_API_KEY --data-file=$tmpG --project=$PROJECT 2>$null
Remove-Item $tmpM, $tmpG -Force
Write-Host "      Done`n" -ForegroundColor Green

# Step 4 — IAM
Write-Host "[4/6] Setting IAM permissions..." -ForegroundColor Yellow
$NUM = gcloud projects describe $PROJECT --format="value(projectNumber)"
$SA  = "$NUM-compute@developer.gserviceaccount.com"
gcloud secrets add-iam-policy-binding MONGODB_URI --member="serviceAccount:$SA" --role="roles/secretmanager.secretAccessor" --project=$PROJECT | Out-Null
gcloud secrets add-iam-policy-binding GOOGLE_API_KEY --member="serviceAccount:$SA" --role="roles/secretmanager.secretAccessor" --project=$PROJECT | Out-Null
Write-Host "      Done`n" -ForegroundColor Green

# Step 5 — Build with NO cache, new tag
Write-Host "[5/6] Building fresh container (no cache, ~5 min)..." -ForegroundColor Yellow
gcloud builds submit --tag $IMAGE --no-cache --project=$PROJECT
Write-Host "      Done`n" -ForegroundColor Green

# Step 6 — Deploy (no --port flag, let Cloud Run use PORT env var)
Write-Host "[6/6] Deploying to Cloud Run..." -ForegroundColor Yellow
gcloud run deploy $SERVICE `
    --image=$IMAGE `
    --region=$REGION `
    --platform=managed `
    --allow-unauthenticated `
    --memory=2Gi `
    --cpu=2 `
    --timeout=300 `
    --min-instances=0 `
    --max-instances=3 `
    --set-secrets="MONGODB_URI=MONGODB_URI:latest,GOOGLE_API_KEY=GOOGLE_API_KEY:latest" `
    --set-env-vars="MALL_NAME=Sunrise Mall,AGENT_MODEL=gemini-2.5-flash" `
    --project=$PROJECT

$URL = gcloud run services describe $SERVICE --region=$REGION --project=$PROJECT --format="value(status.url)"

Write-Host "`n========================================" -ForegroundColor Green
Write-Host " DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host " Live URL : $URL" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Green
