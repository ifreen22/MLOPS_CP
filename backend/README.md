# Backend Application

FastAPI powered Machine Learning inference engine for AIOps Sentinel.

## Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running
```bash
uvicorn app.main:app --reload
```

## Testing
```bash
pytest tests/
```
