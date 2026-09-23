# weather_api.py
# This module handles all interactions with the CWA (Central Weather Administration)
# Open Data API, including fetching weather forecast data for Taiwan's counties and cities.
# The API key is loaded securely from the .env file using python-dotenv.

import os
import json
import warnings
import requests
from dotenv import load_dotenv

# Suppress SSL warnings caused by CWA server's non-standard certificate
# (Missing Subject Key Identifier). This is a known issue with opendata.cwa.gov.tw.
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

# Load environment variables from .env
load_dotenv()

# CWA Open Data API endpoint
# F-C0032-001: 36-hour weather forecast for all Taiwan counties and cities
API_BASE_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001"

# Weather elements to extract from the API response
TARGET_ELEMENTS = {"Wx", "MinT", "MaxT"}


def parse_forecast(data):
    """
    Parse the raw CWA API JSON response into a clean list of forecast records.

    JSON structure (F-C0032-001):
        data
        └── records
            └── location[]              # one entry per county/city
                ├── locationName        # e.g. "臺北市"
                └── weatherElement[]   # one entry per weather type
                    ├── elementName     # e.g. "Wx", "MinT", "MaxT"
                    └── time[]          # 3 time periods for 36-hour forecast
                        ├── startTime
                        ├── endTime
                        └── parameter
                            ├── parameterName   # value label (e.g. "多雲", "25")
                            └── parameterValue  # numeric code for Wx

    Returns:
        list[dict]: One dict per (location, time period) with keys:
            locationName, startTime, endTime, Wx, WxValue, MinT, MaxT
    """
    records = []

    locations = data.get("records", {}).get("location", [])
    if not locations:
        print("[WARN]  No location data found in API response.")
        return records

    for location in locations:
        location_name = location.get("locationName", "Unknown")

        # Build a lookup: elementName -> list of time-period dicts
        elements = {}
        for element in location.get("weatherElement", []):
            name = element.get("elementName")
            if name in TARGET_ELEMENTS:
                elements[name] = element.get("time", [])

        # All elements share the same time slots — use Wx as the index
        wx_times = elements.get("Wx", [])
        mint_times = elements.get("MinT", [])
        maxt_times = elements.get("MaxT", [])

        for i, wx_period in enumerate(wx_times):
            start_time = wx_period.get("startTime", "")
            end_time   = wx_period.get("endTime", "")

            wx_param   = wx_period.get("parameter", {})
            wx_name    = wx_param.get("parameterName", "")   # e.g. "多雲"
            wx_value   = wx_param.get("parameterValue", "")  # e.g. "2"

            mint_param = mint_times[i].get("parameter", {}) if i < len(mint_times) else {}
            maxt_param = maxt_times[i].get("parameter", {}) if i < len(maxt_times) else {}

            min_t = mint_param.get("parameterName", "")  # temperature as string
            max_t = maxt_param.get("parameterName", "")

            records.append({
                "locationName": location_name,
                "startTime":    start_time,
                "endTime":      end_time,
                "Wx":           wx_name,
                "WxValue":      wx_value,
                "MinT":         min_t,
                "MaxT":         max_t,
            })

    return records


def fetch_weather_forecast():
    """
    Fetch the 36-hour weather forecast from CWA Open Data API,
    parse it, and print a readable preview of the results.
    """
    # Step 1: Load API key from environment
    api_key = os.getenv("CWA_API_KEY")
    if not api_key:
        print("[ERROR] CWA_API_KEY is missing or empty in the .env file.")
        print("        Please fill in your API key: CWA_API_KEY=your_key_here")
        return None

    # Step 2: Build request parameters
    params = {
        "Authorization": api_key,
        "format": "JSON",
    }

    print("[INFO] Sending request to CWA Open Data API...")
    print(f"       Endpoint: {API_BASE_URL}\n")

    # Step 3: Make the HTTP GET request
    # Note: verify=False is required because opendata.cwa.gov.tw uses a certificate
    # with a missing Subject Key Identifier that Python's SSL stack rejects.
    try:
        response = requests.get(API_BASE_URL, params=params, timeout=10, verify=False)
    except requests.exceptions.SSLError as e:
        print(f"[ERROR] SSL error: {e}")
        return None
    except requests.exceptions.ConnectionError:
        print("[ERROR] Unable to connect. Please check your internet connection.")
        return None
    except requests.exceptions.Timeout:
        print("[ERROR] Request timed out after 10 seconds.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Unexpected request error: {e}")
        return None

    # Step 4: Check HTTP status code
    print(f"[OK]    HTTP Status Code: {response.status_code}")
    if response.status_code != 200:
        print(f"[ERROR] Expected 200 OK, got {response.status_code}.")
        print(f"        Response body: {response.text[:300]}")
        return None

    # Step 5: Parse JSON response
    try:
        data = response.json()
    except json.JSONDecodeError:
        print("[ERROR] Failed to parse response as JSON.")
        print(f"        Raw response: {response.text[:300]}")
        return None

    # Step 6: Print top-level JSON keys (kept from previous step)
    print(f"[KEYS]  Top-level JSON keys: {list(data.keys())}")

    # Step 7: Parse forecast records
    print("\n[INFO] Parsing forecast data...\n")
    forecast_records = parse_forecast(data)

    if not forecast_records:
        print("[ERROR] No forecast records could be parsed.")
        return None

    # Step 8: Print summary statistics
    locations_found = data.get("records", {}).get("location", [])
    num_locations = len(locations_found)
    num_records   = len(forecast_records)
    periods_each  = num_records // num_locations if num_locations else 0

    print(f"[RESULT] Locations found   : {num_locations}")
    print(f"[RESULT] Total records     : {num_records}  ({periods_each} time periods x {num_locations} locations)")

    # Step 9: Print one example record
    print("\n[EXAMPLE] First parsed record:")
    example = forecast_records[0]
    for key, value in example.items():
        print(f"          {key:<14}: {value}")

    # Step 10: Print a readable table of the first 6 records
    print("\n[PREVIEW] First 6 forecast records:")
    print(f"  {'Location':<10} {'Start':<20} {'End':<20} {'Wx':<10} {'MinT':>5} {'MaxT':>5}")
    print("  " + "-" * 73)
    for rec in forecast_records[:6]:
        print(
            f"  {rec['locationName']:<10} "
            f"{rec['startTime']:<20} "
            f"{rec['endTime']:<20} "
            f"{rec['Wx']:<10} "
            f"{rec['MinT']:>5} "
            f"{rec['MaxT']:>5}"
        )

    return forecast_records


if __name__ == "__main__":
    fetch_weather_forecast()
