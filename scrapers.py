#!/usr/bin/env python3
"""
Interactive web scraper that stores results in JSON and separately stores image URLs.
"""

import json
from pathlib import Path

# Set JSON output file paths
OUTPUT_FILE = Path("scraper_output.json")
IMAGES_FILE = Path("scraper_images.json")

def scrape_url(url: str) -> dict:
    """
    Scrape a web page and return structured data.

    Args:
        url (str): Target webpage URL.

    Returns:
        dict: Scraper output
    """
    try:
        from tools.web_fetcher import WebFetcher
        from tools.content_extractor import ContentExtractor
        from tools.image_extractor import ImageExtractor
        from tools.credibility_checker import CredibilityChecker
        from bs4 import BeautifulSoup

        # Fetch
        fetcher = WebFetcher()
        fetch_result = fetcher.execute(url=url)
        if not fetch_result.get("success"):
            return {"success": False, "error": fetch_result.get("error"), "url": url}

        # Extract text
        extractor = ContentExtractor()
        soup = fetch_result.get("soup") or (BeautifulSoup(fetch_result.get("content", ""), "html.parser"))
        extract_result = extractor.execute(
            soup=soup,
            url=url,
            min_content_length=10,
            strategy_preference="trafilatura"
        )

        # Extract images
        image_extractor = ImageExtractor()
        image_result = image_extractor.execute(soup=soup, base_url=url)

        # Credibility
        credibility_checker = CredibilityChecker()
        credibility_result = credibility_checker.execute(url=url)

        # Assemble output
        text_blocks = extract_result.get("text_blocks", [])
        return {
            "success": True,
            "url": url,
            "title": extract_result.get("title", ""),
            "text": " ".join(block["text"] for block in text_blocks),
            "images": [
                {
                    "src": img["src"],
                    "alt": img["alt"],
                    "context": (img.get("context_text") or "")[:200]
                }
                for img in image_result.get("images", [])
                if img["extraction_metadata"]["in_article"]
                and not any(skip in img["src"].lower()
                            for skip in ["logo", "app-store", "google-play", "inbox", "whatsapp"])
                and img["alt"].lower() not in ["logo", "app-get", "whatsapp", "inbox"]
            ],
            "credibility": credibility_result.get("credibility_report", {}),
            "summary": {
                "blocks": len(text_blocks),
                "chars": sum(block.get("character_count", len(block["text"]))
                             for block in text_blocks),
                "images": len([
                    img for img in image_result.get("images", [])
                    if img["extraction_metadata"]["in_article"]
                ]),
                "quality": round(extract_result.get("extraction_metadata", {}).get("quality_score", 0), 2),
                "credibility_score": credibility_result.get("credibility_report", {}).get("overall_score", 0)
            }
        }

    except Exception as e:
        return {"success": False, "error": str(e), "url": url}


def save_to_json(data: dict):
    """
    Save or update scraped data in OUTPUT_FILE and store all image URLs in a flat list in IMAGES_FILE.
    """
    all_data = {}
    all_images = set()

    # Load existing full data
    if OUTPUT_FILE.exists():
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                all_data = json.load(f)
        except json.JSONDecodeError:
            all_data = {}

    # Load existing image URLs
    if IMAGES_FILE.exists():
        try:
            with open(IMAGES_FILE, "r", encoding="utf-8") as f:
                existing_images = json.load(f)
                all_images.update(existing_images)
        except json.JSONDecodeError:
            all_images = set()

    # Save full scraped data
    url_key = data.get("url", f"url_{len(all_data)+1}")
    all_data[url_key] = data
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
    print(f"Saved full data to {OUTPUT_FILE}")

    # Update and save image URLs
    image_urls = [img["src"] for img in data.get("images", [])]
    all_images.update(image_urls)
    with open(IMAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(list(all_images), f, indent=2, ensure_ascii=False)
    print(f"Saved image URLs to {IMAGES_FILE}")


# -------------------- Interactive Test --------------------
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    else:
        test_url = input("Enter a URL to scrape: ").strip()

    if not test_url.startswith("http"):
        print("Please enter a valid URL starting with http or https.")
        sys.exit(1)

    print(f"Scraping {test_url}...")
    result = scrape_url(test_url)

    if result.get("success"):
        print(f"Scraped {result.get('url')} successfully!")
        print(f"Title: {result.get('title')}")
        print(f"Text length: {len(result.get('text', ''))} characters")
        print(f"Images extracted: {len(result.get('images', []))}")
        print(f"Credibility score: {result.get('summary', {}).get('credibility_score', 'N/A')}")
        save_to_json(result)
    else:
        print(f"Error scraping {test_url}: {result.get('error')}")
