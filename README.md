# Catering and Events Dispatch System

A Flask-based catering equipment dispatch and return reconciliation system for tracking event items, team leader sign-off, missing quantities, and loss value reports.

## Login Accounts

- Admin: `admin` / `Admin@2026`
- Team Leader: `leader` / `Leader@2026`

## Features

- Operations dashboard
- Equipment inventory
- Event dispatch creation
- Team leader dispatch sign-off
- Return reconciliation
- Missing item and loss value reports
- CSV export
- Full-screen login background image

## Run Locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open: `http://127.0.0.1:5053`

## Render Deployment

Render can deploy this repo using `render.yaml`.

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app --bind 0.0.0.0:$PORT`
