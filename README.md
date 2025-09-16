## AGENTIC: News Scraping, Fact-Checking, Image Analysis, and Aggregation

An orchestrated pipeline that:
- Scrapes a news URL for text and images
- Fact-checks image context text with Wikipedia
- Classifies article text with a fake news model
- Evaluates images via Strands tools
- Aggregates everything into concise validity summaries using Bedrock Claude

### Project structure
- `orchestrator.py`: Entry point that runs the full pipeline and prints summaries
- `scrapers.py`: Scrapes text, images, credibility and writes `scraper_output.json` and `scraper_images.json`
- `wiki_fact_checker.py`: Wikipedia-based fact checking → `wiki_fact_check_results.json`
- `fake_news_agent.py`: BERT classifier for fake vs real → `fake_news_analysis.json`
- `kk/agent_tester.py`: Calls `kk/image_agent.py` to evaluate images → `scraper_images_evaluation.json`
- `AI.py`: Aggregates all JSON outputs and asks Claude for a short summary → `news_validity_summary.json`
- `tools/`: HTML fetching, extraction, quality/credibility helpers
- `requirements.txt`: Python dependencies

### Requirements
- macOS or Linux with Python 3.12+
- An AWS account with Bedrock access (Claude model) and credentials available to `boto3`
- A SerpAPI key for reverse image search (used by Strands tools)
- Streamlit (for optional web UI)

### Environment variables

**For local development:** Create an `.env` file at the project root with:
```
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
SERPAPI_KEY=your_serpapi_key
```

**For Streamlit Cloud deployment:** Use the secrets management in your app settings instead of `.env` files.

If you use Bedrock via default AWS environment/CLI profiles, explicit variables may not be required. `AI.py` uses `boto3` default resolution.

### Setup
```bash
python3 -m venv /Users/guanyu/AGENTIC/venv
source /Users/guanyu/AGENTIC/venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Models and language data
python -m spacy download en_core_web_sm
python - << 'PY'
import nltk
for r in ["punkt", "stopwords"]:
    nltk.download(r, quiet=True)
print("NLTK ready")
PY
```

### Streamlit UI
A simple chat-like Streamlit UI is available in `app.py`.

Note: Ensure the project paths in `app.py` point to your local project root. If needed, edit:
```
PROJECT_ROOT = Path("/Users/guanyu/AGENTIC")
```

Run the UI:
```bash
source /Users/guanyu/AGENTIC/venv/bin/activate
streamlit run app.py
```

Usage: paste a URL into the chat input. The UI runs the orchestrator and displays the final summary.

### Run the orchestrator
Provide a URL interactively or via argument. The script prints final summaries to the terminal and saves all JSONs.
```bash
source /Users/guanyu/AGENTIC/venv/bin/activate
python orchestrator.py
# or
python orchestrator.py "https://example.com/news-article"
```

Outputs (written to project root):
- `scraper_output.json`: Full scraped data keyed by URL
- `scraper_images.json`: Flat list of image URLs
- `wiki_fact_check_results.json`: Wikipedia fact-check results
- `fake_news_analysis.json`: Text classification results
- `scraper_images_evaluation.json`: Image evaluation results
- `news_validity_summary.json`: Final Claude summaries per URL

### Notes on models and services
- Fake news model: `jy46604790/Fake-News-Bert-Detect` (downloaded at first run)
- Wikipedia queries via `wikipedia` package
- Strands image evaluation relies on:
  - `strands-agents` and `strands-agents-tools`
  - `SERPAPI_KEY` for reverse image search
- Aggregation in `AI.py` uses Bedrock Claude (`converse` API). Retries with exponential backoff are enabled for throttling.

### Troubleshooting
- Throttling from Bedrock: `AI.py` retries automatically. Consider re-running later or lowering QPS.
- Missing spaCy model: run `python -m spacy download en_core_web_sm`.
- NLTK resources: ensure `punkt` and `stopwords` are downloaded (see Setup above).
- SerpAPI errors: set `SERPAPI_KEY` in `.env` and verify your quota.
- Large files when pushing to GitHub: this repo ignores `venv/` and generated JSONs via `.gitignore`.

### Development
Useful commands:
```bash
# Lint (if you add a linter later)
python -m pyflakes . || true

# Update dependencies
pip install -r requirements.txt

# Git basics
git add -A && git commit -m "Change message" && git push
```

### License
Proprietary. All rights reserved (update as needed).


