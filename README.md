# ReviewRadar 🎯

Find businesses with negative Google reviews that have WhatsApp — and reach out to offer review removal services.

## How It Works
1. Enter city, business type, max rating
2. App scans Google Maps via Apify
3. Checks WhatsApp on each number **first** — skips if no WhatsApp
4. Shows 1-star reviews + screenshots for leads that have WhatsApp

## Deploy on Streamlit Cloud

### Step 1 — GitHub
- Push all files to a GitHub repo

### Step 2 — Streamlit Cloud
- Go to share.streamlit.io
- Connect your GitHub repo
- Set main file: `app.py`

### Step 3 — Secrets
- In Streamlit Cloud → App Settings → Secrets
- Add:
```
APIFY_TOKEN = "your_apify_token_here"
```

### Step 4 — Packages
Make sure `packages.txt` has `chromium` — this installs Chromium for Playwright (WhatsApp check + screenshots).

## Files
- `app.py` — main Streamlit app
- `requirements.txt` — Python dependencies
- `packages.txt` — system dependencies (Chromium)
- `secrets_template.toml` — secrets format reference
