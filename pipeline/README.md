# Pipeline

The data processing engine for “Is AI Good Yet?”.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Run all phases
python run.py --phase all

# Run specific phase
python run.py --phase ingest
```

## Structure

- `src/hn_resolver.py`: Algolia API integration.
- `src/scraper.py`: Content extraction.
- `src/classifier.py`: LLM analysis.
- `src/store/`: Database and Parquet management.
