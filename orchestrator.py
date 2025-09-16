#!/usr/bin/env python3
"""
Orchestrator Agent (Parallel image evaluation)

Workflow:
1) Prompt for a URL to analyze
2) Use scrapers.py to scrape and save outputs to scraper_output.json and scraper_images.json
3) Run wiki_fact_checker.py to generate wiki_fact_check_results.json
4) Run fake_news_agent.py to generate fake_news_analysis.json
5) Run kk/agent_tester.py to evaluate images into scraper_images_evaluation.json (runs in background)
6) Run AI.py to aggregate all JSONs into news_validity_summary.json
"""

import sys
import json
import subprocess
from pathlib import Path

PROJECT_ROOT = Path.cwd()

# File paths used by downstream scripts
SCRAPER_OUTPUT = PROJECT_ROOT / "scraper_output.json"
SCRAPER_IMAGES = PROJECT_ROOT / "scraper_images.json"
WIKI_FACT_OUTPUT = PROJECT_ROOT / "wiki_fact_check_results.json"
FAKE_NEWS_OUTPUT = PROJECT_ROOT / "fake_news_analysis.json"
IMAGE_EVAL_OUTPUT = PROJECT_ROOT / "scraper_images_evaluation.json"
FINAL_SUMMARY_OUTPUT = PROJECT_ROOT / "news_validity_summary.json"


def run_script(script_path: Path):
    """Run a Python script with the current interpreter and raise on failure."""
    completed = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(
            f"Script failed: {script_path}\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
    if completed.stdout:
        print(completed.stdout.rstrip())
    if completed.stderr:
        # Some libraries log to stderr; still surface it for visibility
        print(completed.stderr.rstrip())


def main():
    try:
        # 1) Prompt for URL
        if len(sys.argv) > 1:
            url = sys.argv[1].strip()
        else:
            url = input("Enter a URL to analyze: ").strip()

        if not url.startswith("http"):
            print("Please enter a valid URL starting with http or https.")
            sys.exit(1)

        # 2) Scrape and save JSONs
        print(f"[1/5] Scraping: {url}")
        from scrapers import scrape_url, save_to_json
        scrape_result = scrape_url(url)
        if not scrape_result.get("success"):
            err = scrape_result.get("error", "Unknown error")
            raise RuntimeError(f"Scraping failed for {url}: {err}")
        save_to_json(scrape_result)
        if not SCRAPER_OUTPUT.exists():
            raise FileNotFoundError(f"Expected {SCRAPER_OUTPUT} to be created.")
        if not SCRAPER_IMAGES.exists():
            raise FileNotFoundError(f"Expected {SCRAPER_IMAGES} to be created.")

        # 4) Start image evaluation in background (runs while text checks execute)
        print("[4/5] Evaluating images in background...")
        image_eval_process = subprocess.Popen(
            [sys.executable, str(PROJECT_ROOT / "kk" / "agent_tester.py")],
            stdout=subprocess.DEVNULL,  # ignore console output
            stderr=subprocess.DEVNULL,  # ignore console errors
            text=True
        )

        # 3a) Run Wikipedia fact checker while images are being evaluated
        print("[2/5] Running Wikipedia fact checker...")
        run_script(PROJECT_ROOT / "wiki_fact_checker.py")
        if not WIKI_FACT_OUTPUT.exists():
            raise FileNotFoundError(f"Expected {WIKI_FACT_OUTPUT} to be created.")

        # 3b) Run fake news analysis while images are being evaluated
        print("[3/5] Running fake news analysis...")
        run_script(PROJECT_ROOT / "fake_news_agent.py")
        if not FAKE_NEWS_OUTPUT.exists():
            raise FileNotFoundError(f"Expected {FAKE_NEWS_OUTPUT} to be created.")

        # Wait for image evaluation to finish before aggregation
        image_eval_process.wait()
        if not IMAGE_EVAL_OUTPUT.exists():
            raise FileNotFoundError(f"Expected {IMAGE_EVAL_OUTPUT} to be created.")

        # 6) Aggregate results
        print("[5/5] Aggregating results with AI.py...")
        run_script(PROJECT_ROOT / "AI.py")
        if not FINAL_SUMMARY_OUTPUT.exists():
            raise FileNotFoundError(f"Expected {FINAL_SUMMARY_OUTPUT} to be created.")

        # Print summaries to terminal
        try:
            with open(FINAL_SUMMARY_OUTPUT, "r", encoding="utf-8") as f:
                summaries = json.load(f)
            print("\n=== News Validity Summaries ===")
            for url, entry in summaries.items():
                summary_text = entry.get("summary") or entry.get("error") or "No summary available."
                print(f"\nURL: {url}\n{summary_text}\n" + ("-" * 80))
        except Exception as e:
            print(f"Could not read or print summaries: {e}")

        print(f"\nDone. Final summary saved to: {FINAL_SUMMARY_OUTPUT}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
