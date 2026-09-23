import sys

# Force UTF-8 output so Traditional Chinese characters display correctly
# in terminals that default to cp950 (Windows Traditional Chinese).
sys.stdout.reconfigure(encoding="utf-8")

from weather_api import fetch_weather_forecast
from database import init_db, insert_records, get_all_records

print("=" * 60)
print("  Taiwan Weather Forecast")
print("=" * 60)

# Step 1: Initialize the database (create file + table if needed)
print("\n[STEP 1] Initializing database...")
init_db()

# Step 2: Fetch and parse forecast data from CWA API
print("\n[STEP 2] Fetching forecast data from CWA API...")
forecast_records = fetch_weather_forecast()

if not forecast_records:
    print("[ERROR] Could not retrieve forecast data. Exiting.")
    sys.exit(1)

# Step 3: Insert parsed records into SQLite
print("\n[STEP 3] Inserting records into SQLite...")
insert_records(forecast_records)

# Step 4: Query and print the first 10 rows as verification
print("\n[STEP 4] Querying database — first 10 rows:")
rows = get_all_records()
total_in_db = len(rows)

print(f"\n  Total rows in database : {total_in_db}")
print(f"\n  {'id':>3}  {'Location':<8}  {'Start':<20}  {'End':<20}  {'Wx':<10}  {'MinT':>5}  {'MaxT':>5}")
print("  " + "-" * 78)
for row in rows[:10]:
    print(
        f"  {row['id']:>3}  "
        f"{row['locationName']:<8}  "
        f"{row['startTime']:<20}  "
        f"{row['endTime']:<20}  "
        f"{row['Wx']:<10}  "
        f"{row['MinT']:>5.1f}  "
        f"{row['MaxT']:>5.1f}"
    )

# Step 5: Print one example row as a dict
print("\n[EXAMPLE] Row #1 as dictionary:")
if rows:
    example = dict(rows[0])
    for key, value in example.items():
        print(f"  {key:<14}: {value}")

print("\n[DONE] Pipeline complete.")
