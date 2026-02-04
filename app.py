from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Iterable

import requests
from flask import Flask, flash, redirect, render_template, request, url_for

APP_TITLE = "Jibble Daily Work Report"
DEFAULT_BASE_URL = "https://api.jibble.io/v2"
STANDARD_DAY_HOURS = 8

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret")


@dataclass
class EntryRow:
    property_name: str
    time_in: str
    time_out: str
    total: str


@dataclass
class PersonReport:
    person_name: str
    date_label: str
    rows: list[EntryRow]
    total_worked: str
    balance: str


def _parse_iso8601(value: str | None) -> datetime | None:
    if not value:
        return None
    cleaned = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None


def _format_duration(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    total_minutes = int(seconds // 60)
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours}h {minutes:02d}m"


def _format_time(value: datetime | None) -> str:
    if not value:
        return "-"
    return value.strftime("%H:%M:%S")


def _extract_property(entry: dict[str, Any]) -> str:
    location = entry.get("location")
    if isinstance(location, dict):
        for key in ("name", "label", "title"):
            if location.get(key):
                return str(location[key])
    if isinstance(location, str) and location.strip():
        return location
    project = entry.get("project")
    if isinstance(project, dict) and project.get("name"):
        return str(project["name"])
    if entry.get("note"):
        return str(entry["note"])
    return "Unknown"


def _get_auth_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}


def _fetch_people(session: requests.Session, base_url: str) -> list[dict[str, Any]]:
    response = session.get(f"{base_url}/people")
    response.raise_for_status()
    payload = response.json()
    return payload.get("data", payload)


def _fetch_entries(
    session: requests.Session,
    base_url: str,
    person_id: str,
    date_value: str,
) -> list[dict[str, Any]]:
    params = {
        "person_id": person_id,
        "date": date_value,
    }
    response = session.get(f"{base_url}/time_entries", params=params)
    response.raise_for_status()
    payload = response.json()
    return payload.get("data", payload)


def _build_report(
    person: dict[str, Any],
    entries: Iterable[dict[str, Any]],
    date_label: str,
) -> PersonReport:
    rows: list[EntryRow] = []
    total_seconds = 0.0
    for entry in entries:
        time_in = _parse_iso8601(entry.get("in")) or _parse_iso8601(entry.get("time_in"))
        time_out = _parse_iso8601(entry.get("out")) or _parse_iso8601(entry.get("time_out"))
        if time_in and time_out:
            duration = (time_out - time_in).total_seconds()
        else:
            duration = 0.0
        total_seconds += max(duration, 0.0)
        rows.append(
            EntryRow(
                property_name=_extract_property(entry),
                time_in=_format_time(time_in),
                time_out=_format_time(time_out),
                total=_format_duration(duration),
            )
        )

    if not rows:
        rows.append(
            EntryRow(
                property_name="No records for this day",
                time_in="-",
                time_out="-",
                total=_format_duration(0),
            )
        )

    worked = _format_duration(total_seconds)
    balance_seconds = (STANDARD_DAY_HOURS * 3600) - total_seconds
    balance = _format_duration(balance_seconds)

    person_name = person.get("name") or person.get("full_name") or "Unknown"

    return PersonReport(
        person_name=person_name,
        date_label=date_label,
        rows=rows,
        total_worked=worked,
        balance=balance,
    )


@app.route("/", methods=["GET", "POST"])
def index() -> str:
    if request.method == "POST":
        api_key = request.form.get("api_key", "").strip()
        base_url = request.form.get("base_url", DEFAULT_BASE_URL).strip()
        date_value = request.form.get("date", "").strip()
        if not api_key:
            flash("Enter your Jibble API key to continue.")
            return redirect(url_for("index"))
        if not date_value:
            date_value = datetime.now().strftime("%Y-%m-%d")

        session = requests.Session()
        session.headers.update(_get_auth_headers(api_key))

        try:
            people = _fetch_people(session, base_url)
            reports = []
            for person in people:
                person_id = str(person.get("id"))
                entries = _fetch_entries(session, base_url, person_id, date_value)
                reports.append(_build_report(person, entries, date_value))
        except requests.RequestException as exc:
            flash(f"Unable to fetch data from Jibble: {exc}")
            return redirect(url_for("index"))

        return render_template(
            "report.html",
            title=APP_TITLE,
            reports=reports,
            date_value=date_value,
            base_url=base_url,
        )

    return render_template(
        "index.html",
        title=APP_TITLE,
        date_value=datetime.now().strftime("%Y-%m-%d"),
        base_url=DEFAULT_BASE_URL,
    )


@app.route("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
