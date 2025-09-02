from dotenv import load_dotenv
import os
import boto3
import json
import time
import random
from pathlib import Path
from botocore.exceptions import ClientError

# Load environment variables from .env file
load_dotenv(".env")

# Paths to analysis files
FAKE_NEWS_FILE = Path("/Users/guanyu/AGENTIC/fake_news_analysis.json")
IMAGE_EVAL_FILE = Path("/Users/guanyu/AGENTIC/scraper_images_evaluation.json")
WIKI_FACT_CHECK_FILE = Path("/Users/guanyu/AGENTIC/wiki_fact_check_results.json")
OUTPUT_FILE = Path("/Users/guanyu/AGENTIC/news_validity_summary.json")

# Load JSON files
with open(FAKE_NEWS_FILE, "r", encoding="utf-8") as f:
    fake_news_data = json.load(f)

with open(IMAGE_EVAL_FILE, "r", encoding="utf-8") as f:
    image_data = json.load(f)

with open(WIKI_FACT_CHECK_FILE, "r", encoding="utf-8") as f:
    wiki_data = json.load(f)

# Function to ask Claude via AWS Bedrock
def ask_claude(prompt, system="You are a helpful assistant that can answer questions and help with tasks.", max_retries=6, base_delay=1.0):
    client = boto3.client('bedrock-runtime', region_name='us-east-1')
    for attempt in range(max_retries):
        try:
            response = client.converse(
                modelId="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                system=[{"text": system}],
                inferenceConfig={"temperature": 0, "maxTokens": 200}
            )
            return response['output']['message']['content'][0]['text']
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code in ("ThrottlingException", "Throttling", "TooManyRequestsException") and attempt < max_retries - 1:
                sleep_s = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                time.sleep(sleep_s)
                continue
            raise
        except Exception:
            if attempt < max_retries - 1:
                sleep_s = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                time.sleep(sleep_s)
                continue
            raise

# Combine data and prompt Claude for each article
summary_results = {}
for url in fake_news_data:
    fake_news_entry = fake_news_data.get(url, {})
    wiki_entry = wiki_data.get(url, {})

    # For images, get evaluations related to this URL
    article_image_eval = image_data.get(url, {})
    images_summary = f"Image evaluations: {json.dumps(article_image_eval, indent=0)}"

    prompt = f"""
You are to act as a news validity assessor.

Here is the information for an article ({url}):

1. Fake news analysis: {json.dumps(fake_news_entry, indent=0)}
2. Wikipedia fact-check results: {json.dumps(wiki_entry, indent=0)}
3. Image evaluation data: {images_summary}

Based on these sources, give a concise summary (max 100 words) that states whether the news is likely REAL, FAKE, or MIXED, and explain your reasoning.
"""

    try:
        result = ask_claude(prompt)
        summary_results[url] = {"summary": result}
        # Print the result
        print(f"\nURL: {url}\nSummary:\n{result}\n{'-'*80}")
    except Exception as e:
        summary_results[url] = {"error": str(e)}
        print(f"\nURL: {url}\nError: {str(e)}\n{'-'*80}")
    # Be kind to the API between requests
    time.sleep(0.5)

# Save all results (overwrite existing summaries explicitly)
try:
    if OUTPUT_FILE.exists():
        OUTPUT_FILE.unlink()
except Exception:
    # If deletion fails, proceed to write which will truncate the file
    pass
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(summary_results, f, indent=2, ensure_ascii=False)

print(f"\nSaved news validity summaries to {OUTPUT_FILE}")
