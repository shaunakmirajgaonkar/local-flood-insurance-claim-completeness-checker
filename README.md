# Local Flood Insurance Claim Completeness Checker

A 100% local Streamlit application for organizing household flood-insurance claim evidence and screening documentation completeness before submission review.

## What it does
- Explainable 0–100 claim completeness score
- Four completeness classes
- Evidence checklist by claim
- Photo, receipt, damage-description and repair-estimate signals
- Priority review queue
- Before-vs-after evidence scenarios
- Local CSV import/export
- Markdown report export without optional table libraries
- Synthetic sample data for demonstration

## Local-first design
No external APIs, cloud storage, remote model calls, or mandatory internet services are used. Uploaded CSVs are processed inside the running application.

## Responsible use
This tool does **not** determine coverage, claim validity, settlement value, insurer acceptance, legal entitlement, or compliance. It is an organizational and analytical aid for identifying documentation gaps for further review.

## Run
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest tests/ -q
streamlit run app.py
```
