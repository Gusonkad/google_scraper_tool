
## Project Structure
```
adthena_google_scraper/
├── scraper/
├── queries.py
├── run.py
├── requirements.txt
├── output/
│   ├── 01.html
│   └── summary.json
```

## Install
```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows
# or: source .venv/bin/activate  # Linux/macOS
python -m pip install playwright
python -m playwright install
python -m pip install playwright-stealth
pip install -r requirements.txt
```
## Run
```bash
python run.py
```

## Desktop vs Mobile
Input in console prompt
