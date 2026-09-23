import os
import urllib3

import requests
from dotenv import load_dotenv
from requests.exceptions import SSLError

load_dotenv()

CWA_ENDPOINT = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001"


def _parameter_name(period):
    parameter = period.get("parameter", {}) or {}
    return (
        parameter.get("parameterName")
        or parameter.get("parameterValue")
        or ""
    )


def _parse_element(element):
    """Return normalized period records for one weather element."""
    parsed = []

    for period in element.get("time", []):
        start = period.get("startTime")
        end = period.get("endTime")

        if not start or not end:
            continue

        parsed.append(
            {
                "startTime": start,
                "endTime": end,
                "value": _parameter_name(period),
            }
        )

    return parsed


def _overlap_seconds(a_start, a_end, b_start, b_end):
    """
    Calculate overlap between ISO-like datetime strings.
    CWA timestamps are lexicographically sortable, so pandas is not required here.
    """
    from datetime import datetime

    a_s = datetime.fromisoformat(a_start)
    a_e = datetime.fromisoformat(a_end)
    b_s = datetime.fromisoformat(b_start)
    b_e = datetime.fromisoformat(b_end)

    overlap_start = max(a_s, b_s)
    overlap_end = min(a_e, b_e)

    return max(0.0, (overlap_end - overlap_start).total_seconds())


def _best_value(periods, canonical_start, canonical_end):
    """
    Match an element value to a canonical Wx forecast period.

    Exact start/end matches are preferred. If an element uses a shorter first
    window (for example PoP around an issuance boundary), the period with the
    greatest temporal overlap is used. This prevents creating extra fake
    forecast rows only because one element has a different split.
    """
    if not periods:
        return None

    for item in periods:
        if (
            item["startTime"] == canonical_start
            and item["endTime"] == canonical_end
        ):
            return item["value"]

    best_item = None
    best_overlap = 0.0

    for item in periods:
        overlap = _overlap_seconds(
            canonical_start,
            canonical_end,
            item["startTime"],
            item["endTime"],
        )

        if overlap > best_overlap:
            best_overlap = overlap
            best_item = item

    if best_item is not None and best_overlap > 0:
        return best_item["value"]

    return None


def fetch_weather_forecast():
    """
    Fetch CWA 36-hour county/city forecast data.

    Wx forecast periods are treated as the canonical 3 forecast windows.
    MinT, MaxT, CI, and PoP are matched into those windows by exact time or
    greatest temporal overlap. This avoids the previous problem where joining
    every element's startTime created 4+ mixed forecast rows.
    """
    api_key = os.getenv("CWA_API_KEY")

    if not api_key:
        raise RuntimeError(
            "Missing CWA_API_KEY. Please add it to the .env file."
        )

    params = {
        "Authorization": api_key,
        "format": "JSON",
    }

    try:
        response = requests.get(
            CWA_ENDPOINT,
            params=params,
            timeout=20,
        )
    except SSLError:
        # Fallback for school/lab machines with incomplete CA bundles.
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        response = requests.get(
            CWA_ENDPOINT,
            params=params,
            timeout=20,
            verify=False,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"CWA API request failed: {exc}") from exc

    if response.status_code != 200:
        raise RuntimeError(
            f"CWA API returned HTTP {response.status_code}: "
            f"{response.text[:300]}"
        )

    data = response.json()

    if not data.get("success"):
        raise RuntimeError("CWA API returned success=false.")

    locations = data.get("records", {}).get("location", [])
    forecast_records = []

    for location in locations:
        location_name = location.get("locationName", "")
        element_periods = {}

        for element in location.get("weatherElement", []):
            element_name = element.get("elementName")
            if element_name:
                element_periods[element_name] = _parse_element(element)

        # Wx defines the canonical forecast windows.
        canonical_periods = element_periods.get("Wx", [])

        for period in canonical_periods:
            start_time = period["startTime"]
            end_time = period["endTime"]

            wx = period["value"]
            min_t = _best_value(
                element_periods.get("MinT", []),
                start_time,
                end_time,
            )
            max_t = _best_value(
                element_periods.get("MaxT", []),
                start_time,
                end_time,
            )
            pop = _best_value(
                element_periods.get("PoP", []),
                start_time,
                end_time,
            )
            ci = _best_value(
                element_periods.get("CI", []),
                start_time,
                end_time,
            )

            forecast_records.append(
                {
                    "locationName": location_name,
                    "startTime": start_time,
                    "endTime": end_time,
                    "Wx": wx or "",
                    "MinT": float(min_t) if min_t not in (None, "") else None,
                    "MaxT": float(max_t) if max_t not in (None, "") else None,
                    "PoP": float(pop) if pop not in (None, "") else None,
                    "CI": ci or "",
                }
            )

    return forecast_records


if __name__ == "__main__":
    rows = fetch_weather_forecast()
    print(f"Parsed {len(rows)} records.")
    for row in rows[:8]:
        print(row)
