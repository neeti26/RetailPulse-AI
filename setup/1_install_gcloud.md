# Step 1 — Install Google Cloud CLI (Windows)

## Option A: Installer (Easiest)
1. Download: https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe
2. Run the installer — keep all defaults
3. When it finishes, it opens a terminal and runs `gcloud init` automatically
4. Sign in with your Google account when prompted

## Option B: PowerShell (one command)
```powershell
(New-Object Net.WebClient).DownloadFile("https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe", "$env:Temp\GoogleCloudSDKInstaller.exe"); & $env:Temp\GoogleCloudSDKInstaller.exe
```

## After installing, open a NEW terminal and run:
```bash
gcloud init
gcloud auth login
gcloud auth application-default login
```

Then come back and run `setup/2_gcloud_setup.ps1`
