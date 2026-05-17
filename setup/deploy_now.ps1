# RetailPulse AI — Full Cloud Run Deployment
# Run this from the project folder in PowerShell:
#   .\setup\deploy_now.ps1

$ErrorActionPreference = "Stop"
$GCLOUD = "C:\Users\neeti\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
$PROJECT = "gen-lang-client-0047156954"
$REGION = "us-central1"
$SERVICE = "retailpulse-ai"
$REPO = "retailpulse"
$MONGO_URI = "mongodb+srv://retailpulse:kO9ZqcXf9GfEjhAt@retailpulse-cluster.vr4ivqg.mongodb.net/retailpulse"
$GEMINI_KEY = "AIzaSyCnT6mtPfzDm2vk_B8qx3Awk7f-X7LLo3U"
$IMAGE = "$REGION-docker.pkg.dev/$PROJECT/$REPO/$SERVICE`:latest"

Write-Host "`n🚀 RetailPulse AI — Cloud Run Deployment" -ForegroundColor Cyan
Write-Host "   Project : $PROJECT"
Write-Host "   Region  : $REGION"
Write-Host "   Image   : $IMAGE`n"

# 1. Enable APIs
Write-Host "1/6 Enabling APIs..." -ForegroundColor Yellow
& $GCLOUD services enable run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com cloudbuild.googleapis.com --project=$PROJECT
Write-Host "    APIs enabled" -ForegroundColor Green

# 2. Create Artifact Registry repo
Write-Host "2/6 Creating Artifact Registry repo..." -ForegroundColor Yellow
& $GCLOUD artifacts repositories create $REPO `
    --repository-format=docker `
    --location=$REGION `
    --project=$PROJECT 2>$null
Write-Host "    Repo ready" -ForegroundColor Green

# 3. Store secrets
Write-Host "3/6 Storing secrets..." -ForegroundColor Yellow

$tmpMongo = [System.IO.Path]::GetTempFileName()
$tmpGemini = [System.IO.Path]::GetTempFileName()
[System.IO.File]::WriteAllText($tmpMongo, $MONGO_URI, [System.Text.Encoding]::UTF8)
[System.IO.File]::WriteAllText($tmpGemini, $GEMINI_KEY, [System.Text.Encoding]::UTF8)

& $GCLOUD secrets create MONGODB_URI --data-file=$tmpMongo --project=$PROJECT 2>$null
if ($LASTEXITCODE -ne 0) {
    & $GCLOUD secrets versions add MONGODB_URI --data-file=$tmpMongo --project=$PROJECT
}

& $GCLOUD secrets create GOOGLE_API_KEY --data-file=$tmpGemini --project=$PROJECT 2>$null
if ($LASTEXITCODE -ne 0) {
    & $GCLOUD secrets versions add GOOGLE_API_KEY --data-file=$tmpGemini --project=$PROJECT
}

Remove-Item $tmpMongo, $tmpGemini -Force
Write-Host "    Secrets stored" -ForegroundColor Green

# 4. Grant Cloud Run access to secrets
Write-Host "4/6 Setting IAM permissions..." -ForegroundColor Yellow
$PROJECT_NUMBER = & $GCLOUD projects describe $PROJECT --format="value(projectNumber)"
$SA = "$PROJECT_NUMBER-compute@developer.gserviceaccount.com"

& $GCLOUD secrets add-iam-policy-binding MONGODB_URI `
    --member="serviceAccount:$SA" --role="roles/secretmanager.secretAccessor" `
    --project=$PROJECT | Out-Null

& $GCLOUD secrets add-iam-policy-binding GOOGLE_API_KEY `
    --member="serviceAccount:$SA" --role="roles/secretmanager.secretAccessor" `
    --project=$PROJECT | Out-Null
Write-Host "    IAM set" -ForegroundColor Green

# 5. Build container with Cloud Build
Write-Host "5/6 Building container (3-5 min)..." -ForegroundColor Yellow
& $GCLOUD builds submit --tag $IMAGE --project=$PROJECT --machine-type=E2_HIGHCPU_8 .
Write-Host "    Container built" -ForegroundColor Green

# 6. Deploy to Cloud Run
Write-Host "6/6 Deploying to Cloud Run..." -ForegroundColor Yellow
& $GCLOUD run deploy $SERVICE `
    --image=$IMAGE `
    --region=$REGION `
    --platform=managed `
    --allow-unauthenticated `
    --port=7860 `
    --memory=2Gi `
    --cpu=2 `
    --timeout=300 `
    --min-instances=0 `
    --max-instances=3 `
    --set-secrets="MONGODB_URI=MONGODB_URI:latest,GOOGLE_API_KEY=GOOGLE_API_KEY:latest" `
    --set-env-vars="MALL_NAME=Sunrise Mall,AGENT_MODEL=gemini-2.5-flash,UI_PORT=7860" `
    --project=$PROJECT

$URL = & $GCLOUD run services describe $SERVICE --region=$REGION --project=$PROJECT --format="value(status.url)"

Write-Host "`n" 
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "✅  DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "🌐  Live URL : $URL" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "Paste this URL on Devpost as your hosted project link`n"
