# RetailPulse AI — Google Cloud Setup Script
# Run this AFTER installing gcloud CLI and running `gcloud init`
# Usage: .\setup\2_gcloud_setup.ps1 -ProjectId "your-project-id" -MongoUri "mongodb+srv://..." -GeminiKey "AIza..."

param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectId,

    [Parameter(Mandatory=$true)]
    [string]$MongoUri,

    [Parameter(Mandatory=$true)]
    [string]$GeminiKey,

    [string]$Region = "us-central1",
    [string]$ServiceName = "retailpulse-ai",
    [string]$MallName = "Sunrise Mall"
)

$ErrorActionPreference = "Stop"

Write-Host "`n🚀 RetailPulse AI — Google Cloud Deployment" -ForegroundColor Cyan
Write-Host "   Project : $ProjectId"
Write-Host "   Region  : $Region"
Write-Host "   Service : $ServiceName`n"

# ── 1. Set project ──────────────────────────────────────────────────────────
Write-Host "1/7 Setting active project..." -ForegroundColor Yellow
gcloud config set project $ProjectId

# ── 2. Enable APIs ──────────────────────────────────────────────────────────
Write-Host "2/7 Enabling required APIs (this takes ~60s)..." -ForegroundColor Yellow
gcloud services enable `
    run.googleapis.com `
    artifactregistry.googleapis.com `
    secretmanager.googleapis.com `
    cloudbuild.googleapis.com

# ── 3. Create Artifact Registry repo ────────────────────────────────────────
Write-Host "3/7 Creating Artifact Registry repository..." -ForegroundColor Yellow
gcloud artifacts repositories create retailpulse `
    --repository-format=docker `
    --location=$Region `
    --description="RetailPulse AI container images" 2>$null
Write-Host "   (repository already exists or was created)" -ForegroundColor Gray

# ── 4. Store secrets ─────────────────────────────────────────────────────────
Write-Host "4/7 Storing secrets in Secret Manager..." -ForegroundColor Yellow

# MongoDB URI
$MongoUri | gcloud secrets create MONGODB_URI --data-file=- 2>$null
if ($LASTEXITCODE -ne 0) {
    $MongoUri | gcloud secrets versions add MONGODB_URI --data-file=-
}
Write-Host "   ✅ MONGODB_URI stored"

# Gemini API Key
$GeminiKey | gcloud secrets create GOOGLE_API_KEY --data-file=- 2>$null
if ($LASTEXITCODE -ne 0) {
    $GeminiKey | gcloud secrets versions add GOOGLE_API_KEY --data-file=-
}
Write-Host "   ✅ GOOGLE_API_KEY stored"

# ── 5. Grant Cloud Run access to secrets ─────────────────────────────────────
Write-Host "5/7 Granting Cloud Run service account access to secrets..." -ForegroundColor Yellow
$ProjectNumber = gcloud projects describe $ProjectId --format="value(projectNumber)"
$ServiceAccount = "$ProjectNumber-compute@developer.gserviceaccount.com"

gcloud secrets add-iam-policy-binding MONGODB_URI `
    --member="serviceAccount:$ServiceAccount" `
    --role="roles/secretmanager.secretAccessor" | Out-Null

gcloud secrets add-iam-policy-binding GOOGLE_API_KEY `
    --member="serviceAccount:$ServiceAccount" `
    --role="roles/secretmanager.secretAccessor" | Out-Null

Write-Host "   ✅ IAM bindings set"

# ── 6. Build and push container ──────────────────────────────────────────────
Write-Host "6/7 Building container with Cloud Build (this takes 3-5 min)..." -ForegroundColor Yellow
$ImageTag = "$Region-docker.pkg.dev/$ProjectId/retailpulse/retailpulse-ai:latest"

gcloud builds submit `
    --tag $ImageTag `
    --machine-type=E2_HIGHCPU_8 `
    .

Write-Host "   ✅ Container built and pushed: $ImageTag"

# ── 7. Deploy to Cloud Run ───────────────────────────────────────────────────
Write-Host "7/7 Deploying to Cloud Run..." -ForegroundColor Yellow
gcloud run deploy $ServiceName `
    --image=$ImageTag `
    --region=$Region `
    --platform=managed `
    --allow-unauthenticated `
    --port=7860 `
    --memory=2Gi `
    --cpu=2 `
    --timeout=300 `
    --min-instances=0 `
    --max-instances=3 `
    --set-secrets="MONGODB_URI=MONGODB_URI:latest,GOOGLE_API_KEY=GOOGLE_API_KEY:latest" `
    --set-env-vars="MALL_NAME=$MallName,AGENT_MODEL=gemini-2.5-flash,UI_PORT=7860"

# ── Done ─────────────────────────────────────────────────────────────────────
$ServiceUrl = gcloud run services describe $ServiceName --region=$Region --format="value(status.url)"

Write-Host "`n✅ DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "🌐 Live URL : $ServiceUrl" -ForegroundColor Cyan
Write-Host "📋 Devpost  : Paste the URL above as your hosted project link"
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "`nNext steps:"
Write-Host "  1. Open $ServiceUrl to verify the app is running"
Write-Host "  2. Run the seed script against your Atlas cluster"
Write-Host "  3. Record your demo video"
