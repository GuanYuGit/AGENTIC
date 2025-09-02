import json
import os
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import re
from tqdm import tqdm

class FakeNewsDetector:
    def __init__(self, model_name="jy46604790/Fake-News-Bert-Detect"):
        print(f"Loading model: {model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()
        print(f"Model loaded on: {self.device}")

    def preprocess_text(self, text):
        if not text or not isinstance(text, str):
            return ""
        text = re.sub(r'http\S+', '', text)
        text = re.sub(r'[^a-zA-Z0-9\s.,!?]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def analyze_text(self, text):
        if not text or not isinstance(text, str):
            return {"error": "Invalid text input"}

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
                "confidence": probabilities[predicted_class_id].item(),
                "probabilities": {
                    "FAKE": probabilities[0].item(),
                    "REAL": probabilities[1].item()
                },
                "text_preview": cleaned_text[:200] + "..." if len(cleaned_text) > 200 else cleaned_text
            }

        except Exception as e:
            return {"error": f"Analysis failed: {str(e)}"}

    def process_scraper_output(self, scraper_data):
        """
        Convert raw scraper output into a format for FakeNewsDetector
        """
        if not isinstance(scraper_data, dict):
            return {"error": "Invalid scraper data format"}

        url = scraper_data.get("url", "Unknown URL")
        title = scraper_data.get("title", "")

        # Combine text content
        text_content = scraper_data.get("text", "")
        if title:
            text_content = title + ". " + text_content

        if not text_content.strip():
            return {"error": "No text content found", "url": url, "title": title}

        analysis_result = self.analyze_text(text_content)

        return {
            "url": url,
            "title": title,
            "analysis": analysis_result,
            "source_data": {
                "text_preview": text_content[:200] + "..." if len(text_content) > 200 else text_content,
                "text_length": len(text_content)
            }
        }

    def process_json_file(self, json_file_path):
        """
        Read the scraper JSON file and process each article
        """
        if not os.path.exists(json_file_path):
            print(f"Error: File {json_file_path} does not exist")
            return None

        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error loading JSON file: {e}")
            return None

        results = []
        # Ensure it's a list (supporting batch scraping)
        articles = data if isinstance(data, list) else [data]

        for article in tqdm(articles, desc="Analyzing articles"):
            result = self.process_scraper_output(article)
            results.append(result)

        return results


def save_results(results, output_file):
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"Results saved to {output_file}")
    except Exception as e:
        print(f"Error saving results: {e}")


if __name__ == "__main__":
    detector = FakeNewsDetector()

    input_file = "scraper_output.json"  # The file saved by your scraper
    output_file = "fake_news_analysis_results.json"

    results = detector.process_json_file(input_file)
    if results:
        save_results(results, output_file)
