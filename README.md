# Strava → Google Sheets Sync

Automatically syncs your Strava runs (distance + avg HR) into your training plan Google Sheet daily.

## Setup

### 1. Create a GitHub repository
- Go to github.com → New repository (private)
- Upload these files: `strava_sync.py`, `requirements.txt`, `.github/workflows/strava_sync.yml`

### 2. Add GitHub Secrets
Go to your repo → Settings → Secrets and variables → Actions → New repository secret

Add these 5 secrets:

| Secret Name | Value |
|---|---|
| `STRAVA_CLIENT_ID` | Your Strava app Client ID |
| `STRAVA_CLIENT_SECRET` | Your Strava app Client Secret |
| `STRAVA_REFRESH_TOKEN` | Your Strava refresh token |
| `GOOGLE_SHEET_ID` | `1Ka_31tFYz_oqP-h-PUQv7RjOO6cnNaLu` |
| `GOOGLE_CREDENTIALS_JSON` | The entire contents of your service account JSON file |

> **Tip**: For `GOOGLE_CREDENTIALS_JSON`, open the .json file in a text editor, select all, and paste the entire contents as the secret value.

### 3. Share your Google Sheet
Make sure your Google Sheet is shared with:
`strava@strava-sync-489700.iam.gserviceaccount.com` (Editor access)

### 4. Run it
- **Automatic**: Runs every day at 2am UTC (10am Sydney time)
- **Manual**: Go to Actions tab → Strava Sync → Run workflow

## What it does
- Fetches all your Strava runs
- Matches each run to a row in the "Plan" sheet by date
- Updates **Actual Avg HR (bpm)** and **Actual Distance (km)** columns
- If you ran twice in a day, it keeps the longer run
