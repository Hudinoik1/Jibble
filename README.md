# Jibble Daily Work Report

A lightweight Flask app that connects to the Jibble API and generates daily work reports per person.

## Features
- Enter Jibble API credentials and optionally a custom base URL.
- Pick any date and refresh reports on demand.
- Per-person tables showing property, time in/out, totals, and an 8-hour balance.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open `http://localhost:5000`.

## Deploy on Render

This repo includes a `render.yaml` so you can deploy quickly:

1. Create a new **Web Service** in Render.
2. Point it at this repo.
3. Render will use the `render.yaml` file to install dependencies and run Gunicorn.

Set a `FLASK_SECRET` environment variable in Render for session security.

## Notes
- The app expects a Jibble API token with access to `people` and `time_entries` endpoints.
- Property names are derived from `location`, `project`, or `note` fields when available.
