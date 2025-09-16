import json
from pathlib import Path
from image_agent import evaluate_image

# Paths to input and output files
IMAGES_FILE = Path("scraper_images.json")
OUTPUT_FILE = Path("scraper_images_evaluation.json")

# Load image URLs from JSON
if not IMAGES_FILE.exists():
    raise FileNotFoundError(f"{IMAGES_FILE} not found.")

with open(IMAGES_FILE, "r", encoding="utf-8") as f:
    image_urls = json.load(f)

# Ensure we have a list
if not isinstance(image_urls, list):
    raise ValueError("Expected a list of image URLs in scraper_images.json")

# Evaluate each image
results = {}
for url in image_urls:
    try:
        eval_result = evaluate_image(url)
        results[url] = eval_result
    except Exception as e:
        results[url] = {"error": str(e)}

# Save evaluation results to JSON
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"Saved image evaluation results to {OUTPUT_FILE}")
