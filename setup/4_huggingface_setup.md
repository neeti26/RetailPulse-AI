# Step 4 — Hugging Face Spaces (Backup Demo URL)

Hugging Face Spaces gives you a free public URL for your Gradio app.
Use this as your second "Try it out" link on Devpost.

## A. Create a Hugging Face Account
Go to https://huggingface.co/join and sign up (free).

## B. Create a New Space

1. Go to https://huggingface.co/new-space
2. **Space name**: `RetailPulse-AI`
3. **License**: Apache 2.0
4. **SDK**: Gradio
5. **Hardware**: CPU Basic (free)
6. **Visibility**: Public
7. Click **Create Space**

## C. Add Secrets

In your Space → **Settings** → **Variables and secrets** → **New secret**:

| Name | Value |
|---|---|
| `MONGODB_URI` | your Atlas connection string |
| `GOOGLE_API_KEY` | your Gemini API key |
| `MALL_NAME` | Sunrise Mall |
| `AGENT_MODEL` | gemini-2.5-flash |

## D. Push Your Code to the Space

Hugging Face Spaces use git. Run these commands from your project folder:

```bash
# Install git-lfs (required by HuggingFace)
# Download from: https://git-lfs.com/ and install

# Add HuggingFace as a second remote
git remote add huggingface https://huggingface.co/spaces/YOUR_HF_USERNAME/RetailPulse-AI

# Push to HuggingFace (it will ask for your HF username + token)
git push huggingface main
```

To get your HuggingFace token:
1. https://huggingface.co/settings/tokens
2. **New token** → name it `retailpulse` → role: **Write**
3. Copy the token — use it as the password when git asks

## E. Add requirements.txt for Spaces

HuggingFace Spaces reads `requirements.txt` automatically.
Your existing `requirements.txt` already works — no changes needed.

## F. Your Space URL

Once deployed (takes ~3 minutes), your app will be at:
```
https://YOUR_HF_USERNAME-retailpulse-ai.hf.space
```

Add this as the second "Try it out" link on Devpost.

## Note on Cold Starts

Free HF Spaces pause after 48h of inactivity. If the demo URL shows
"This Space is sleeping", click **Restart this Space** — it wakes in ~30s.
Cloud Run is your primary URL; HF is the backup.
