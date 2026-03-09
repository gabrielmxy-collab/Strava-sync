import os
import requests
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timezone
import json

# --- Config from environment variables ---
STRAVA_CLIENT_ID = os.environ["STRAVA_CLIENT_ID"]
STRAVA_CLIENT_SECRET = os.environ["STRAVA_CLIENT_SECRET"]
STRAVA_REFRESH_TOKEN = os.environ["STRAVA_REFRESH_TOKEN"]
GOOGLE_SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
GOOGLE_CREDENTIALS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]

SHEET_NAME = "Plan"


def get_strava_token():
    resp = requests.post("https://www.strava.com/oauth/token", data={
        "client_id": STRAVA_CLIENT_ID,
        "client_secret": STRAVA_CLIENT_SECRET,
        "refresh_token": STRAVA_REFRESH_TOKEN,
        "grant_type": "refresh_token"
    })
    resp.raise_for_status()
    return resp.json()["access_token"]


def get_strava_activities(token):
    headers = {"Authorization": f"Bearer {token}"}
    activities = []
    page = 1
    while True:
        resp = requests.get(
            "https://www.strava.com/api/v3/athlete/activities",
            headers=headers,
            params={"per_page": 100, "page": page}
        )
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        activities.extend(data)
        page += 1
    return activities


def build_activity_map(activities):
    """Map date string (YYYY-MM-DD) -> {distance_km, avg_hr, avg_pace}"""
    activity_map = {}
    for a in activities:
        if a.get("type") not in ("Run", "VirtualRun"):
            continue
        date_str = a["start_date_local"][:10]
        distance_km = round(a["distance"] / 1000, 2)
        avg_hr = a.get("average_heartrate")
        # average_speed is in m/s -> convert to min/km
        avg_speed = a.get("average_speed")
        if avg_speed and avg_speed > 0:
            pace_sec_per_km = 1000 / avg_speed
            pace_min = int(pace_sec_per_km // 60)
            pace_sec = int(pace_sec_per_km % 60)
            avg_pace = f"{pace_min}:{pace_sec:02d}"
        else:
            avg_pace = None
        # If multiple runs on same day, keep the longer one
        if date_str not in activity_map or distance_km > activity_map[date_str]["distance_km"]:
            activity_map[date_str] = {
                "distance_km": distance_km,
                "avg_hr": round(avg_hr) if avg_hr else None,
                "avg_pace": avg_pace
            }
    return activity_map


def normalize_date(raw):
    """Convert various date formats to YYYY-MM-DD string."""
    if not raw:
        return None
    raw = str(raw).strip()
    for fmt in ("%d-%b-%Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    try:
        from datetime import timedelta
        serial = int(raw)
        base = datetime(1899, 12, 30)
        return (base + timedelta(days=serial)).strftime("%Y-%m-%d")
    except Exception:
        pass
    return None


def sync_to_sheet(activity_map):
    creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    )
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(GOOGLE_SHEET_ID).worksheet(SHEET_NAME)

    all_rows = sheet.get_all_values()
    header = all_rows[0]

    def col_index(name):
        for i, h in enumerate(header):
            if name.lower() in h.lower():
                return i
        return None

    date_col = col_index("date")
    hr_col = col_index("actual avg hr")
    dist_col = col_index("planned distance")
    pace_col = col_index("average pace")

    if date_col is None: date_col = 1
    if hr_col is None: hr_col = 10
    if dist_col is None: dist_col = 8

    updates = []
    updated_count = 0

    for row_idx, row in enumerate(all_rows[1:], start=2):
        if date_col >= len(row):
            continue
        raw_date = row[date_col]
        date_str = normalize_date(raw_date)
        if not date_str or date_str not in activity_map:
            continue

        activity = activity_map[date_str]

        if activity["avg_hr"] is not None:
            updates.append({
                "range": gspread.utils.rowcol_to_a1(row_idx, hr_col + 1),
                "values": [[activity["avg_hr"]]]
            })

        updates.append({
            "range": gspread.utils.rowcol_to_a1(row_idx, dist_col + 1),
            "values": [[activity["distance_km"]]]
        })

        if pace_col is not None and activity["avg_pace"] is not None:
            updates.append({
                "range": gspread.utils.rowcol_to_a1(row_idx, pace_col + 1),
                "values": [[activity["avg_pace"]]]
            })

        updated_count += 1
        print(f"  Row {row_idx} ({date_str}): {activity['distance_km']} km, HR={activity['avg_hr']}, Pace={activity['avg_pace']}")

    if updates:
        sheet.batch_update(updates)
        print(f"\n✅ Updated {updated_count} rows in Google Sheets.")
    else:
        print("ℹ️  No matching activities found to update.")


def main():
    print("🔑 Getting Strava token...")
    token = get_strava_token()

    print("🏃 Fetching Strava activities...")
    activities = get_strava_activities(token)
    print(f"   Found {len(activities)} total activities")

    activity_map = build_activity_map(activities)
    print(f"   {len(activity_map)} unique run dates")

    print("📊 Syncing to Google Sheets...")
    sync_to_sheet(activity_map)


if __name__ == "__main__":
    main()
