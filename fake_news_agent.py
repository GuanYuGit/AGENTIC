#!/usr/bin/env python3
"""
Fake News Agent
Analyzes text content from scraped articles to detect if news is fake or real.
"""

import re
import json
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

class FakeNewsAgent:
    name = "fake_news_agent"
    description = "Analyzes text content to detect if a news article is fake or real."

    def __init__(self, model_name="jy46604790/Fake-News-Bert-Detect"):
        print(f"[FakeNewsAgent] Loading model: {model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()
        print(f"[FakeNewsAgent] Model loaded on: {self.device}")

    def preprocess_text(self, text: str) -> str:
        if not text or not isinstance(text, str):
            return ""
        text = re.sub(r'http\S+', '', text)  # remove URLs
        text = re.sub(r'[^a-zA-Z0-9\s.,!?]', '', text)  # remove non-alphanum
        text = re.sub(r'\s+', ' ', text).strip()  # collapse whitespace
        return text

    def analyze_text(self, text: str) -> dict:
        cleaned_text = self.preprocess_text(text)
        if not cleaned_text:
            return {"error": "Text is empty after preprocessing"}

        try:
            inputs = self.tokenizer(
                cleaned_text,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=512
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.model(**inputs)

            probabilities = torch.softmax(outputs.logits, dim=1)[0]
            predicted_class_id = torch.argmax(probabilities).item()
            label = "FAKE" if predicted_class_id == 0 else "REAL"

            return {
                "prediction": label,
                "confidence": float(probabilities[predicted_class_id].item()),
                "probabilities": {
                    "FAKE": float(probabilities[0].item()),
                    "REAL": float(probabilities[1].item())
                },
                "text_preview": cleaned_text[:200] + "..." if len(cleaned_text) > 200 else cleaned_text
            }

        except Exception as e:
            return {"error": f"Analysis failed: {str(e)}"}

    def __call__(self, scraper_output: dict) -> dict:
        """
        Accepts a single scraped article (dict) and returns analysis.
        """
        if not isinstance(scraper_output, dict):
            return {"error": "Invalid input, expected scraper output as dict"}

        url = scraper_output.get("url", "Unknown URL")
        title = scraper_output.get("title", "")
        text_content = scraper_output.get("text", "")

        if title:
            text_content = title + ". " + text_content

        if not text_content.strip():
            return {"error": "No text content found", "url": url, "title": title}

        analysis = self.analyze_text(text_content)

        return {
            "url": url,
            "title": title,
            "analysis": analysis,
            "source_data": {
                "text_preview": text_content[:200] + "..." if len(text_content) > 200 else text_content,
                "text_length": len(text_content)
            }
        }


# -------------------- Script to analyze JSON --------------------
if __name__ == "__main__":
    # Paths
    SCRAPER_JSON = Path("scraper_output.json")
    OUTPUT_JSON = Path("fake_news_analysis.json")

    # Load scraped articles
    if not SCRAPER_JSON.exists():
        raise FileNotFoundError(f"{SCRAPER_JSON} not found.")

    with open(SCRAPER_JSON, "r", encoding="utf-8") as f:
        scraped_articles = json.load(f)

    if not isinstance(scraped_articles, dict):
        raise ValueError("Expected a dictionary of scraped articles in scraper_output.json")

    # Initialize agent
    agent = FakeNewsAgent()

    # Analyze each article
    analysis_results = {}
    for url, article in scraped_articles.items():
        try:
            result = agent(article)
            analysis_results[url] = result
        except Exception as e:
            analysis_results[url] = {"error": str(e)}

    # Save results
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(analysis_results, f, indent=2, ensure_ascii=False)

    print(f"Saved fake news analysis to {OUTPUT_JSON}")
