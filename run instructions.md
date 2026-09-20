# Run Instructions

```bash
cd LocalFloodInsuranceClaimCompletenessChecker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest tests/ -q
streamlit run app.py
```
