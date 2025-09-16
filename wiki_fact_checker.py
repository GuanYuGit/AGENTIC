#!/usr/bin/env python3
"""
Wiki Fact Checker
Analyzes image context and text from scraped articles against Wikipedia.
"""

import re
import wikipedia
import logging
from difflib import SequenceMatcher
from datetime import datetime
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
import spacy
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# spaCy
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.warning("spaCy model not found. Install with: python -m spacy download en_core_web_sm")
    nlp = None
    # Try to download the model automatically
    try:
        import subprocess
        subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], check=True)
        nlp = spacy.load("en_core_web_sm")
        logger.info("Successfully downloaded and loaded spaCy model")
    except Exception as e:
        logger.warning(f"Failed to download spaCy model: {e}")
        nlp = None

# nltk resources
import nltk
for resource in ["punkt", "stopwords"]:
    try:
        nltk.data.find(f"tokenizers/{resource}" if resource=="punkt" else f"corpora/{resource}")
    except LookupError:
        nltk.download(resource)

@dataclass
class FactCheckResult:
    claim: str
    source: str
    confidence: float
    verdict: str
    evidence: List[str]
    wikipedia_page: Optional[str] = None
    similarity_score: Optional[float] = None
    timestamp: str = None

class ContextFactChecker:
    def __init__(self):
        self.wikipedia_cache = {}

    def extract_context_claims(self, scraper_json: Dict[str, Any], max_sentence_length: int = 300) -> List[str]:
        claims = []
        if "images" in scraper_json:
            for img in scraper_json["images"]:
                if "context" in img and img["context"]:
                    for s in sent_tokenize(img["context"]):
                        claims.append(s[:max_sentence_length])
        return list({c.strip() for c in claims if c.strip()})

    def preprocess_claim(self, claim: str) -> str:
        claim = re.sub(r'\s+', ' ', claim.strip())
        prefixes_to_remove = [
            "According to", "It is reported that", "Sources say",
            "It has been claimed that", "Some say", "Many believe"
        ]
        for prefix in prefixes_to_remove:
            if claim.lower().startswith(prefix.lower()):
                claim = claim[len(prefix):].strip()
                break
        return claim

    def extract_key_entities(self, text: str) -> List[str]:
        if nlp is None:
            words = word_tokenize(text)
            stop_words = set(stopwords.words('english'))
            return [w for w in words if w[0].isupper() and w.lower() not in stop_words][:5]
        doc = nlp(text)
        return [ent.text for ent in doc.ents if ent.label_ in ['PERSON', 'ORG', 'GPE', 'LOC', 'EVENT']]

    def search_wikipedia(self, query: str) -> Optional[Dict[str, Any]]:
        try:
            if len(query) > 300:
                query = query[:300]
            results = wikipedia.search(query, results=5)
            if not results:
                return None
            title = results[0]
            if title in self.wikipedia_cache:
                return self.wikipedia_cache[title]
            page = wikipedia.page(title, auto_suggest=False)
            result = {'title': page.title, 'summary': page.summary, 'content': page.content[:5000], 'url': page.url}
            self.wikipedia_cache[title] = result
            return result
        except Exception as e:
            logger.error(f"Error searching Wikipedia: {e}")
            return None

    def calculate_similarity(self, claim: str, wiki_content: str) -> float:
        similarity = SequenceMatcher(None, claim.lower(), wiki_content.lower()).ratio()
        claim_entities = set(self.extract_key_entities(claim))
        wiki_entities = set(self.extract_key_entities(wiki_content))
        if claim_entities and wiki_entities:
            overlap = len(claim_entities.intersection(wiki_entities)) / len(claim_entities.union(wiki_entities))
            similarity = (similarity*0.3) + (overlap*0.7)
        claim_words = set(claim.lower().split())
        wiki_words = set(wiki_content.lower().split())
        word_overlap = len(claim_words.intersection(wiki_words))/len(claim_words) if claim_words else 0
        return min(max(similarity, word_overlap*0.5), 1.0)

    def fact_check_claim(self, claim: str) -> FactCheckResult:
        claim = self.preprocess_claim(claim)
        if len(claim) < 10:
            return FactCheckResult(claim, "Wikipedia", 0.0, "NEUTRAL", ["Claim too short"], timestamp=datetime.now().isoformat())
        entities = self.extract_key_entities(claim)
        search_queries = [claim] + entities[:3]
        best_result, best_similarity = None, 0.0
        for query in search_queries:
            if len(query) < 3:
                continue
            wiki = self.search_wikipedia(query)
            if wiki:
                sim = self.calculate_similarity(claim, wiki['content'])
                if sim > best_similarity:
                    best_similarity, best_result = sim, wiki
        if best_result is None:
            verdict, confidence, evidence = "NOT_FOUND", 0.0, ["No Wikipedia info found"]
        elif best_similarity > 0.3:
            verdict, confidence, evidence = "SUPPORTED", best_similarity, [f"Found info in {best_result['title']}"]
        elif best_similarity > 0.15:
            verdict, confidence, evidence = "NEUTRAL", best_similarity, [f"Some info found in {best_result['title']}"]
        else:
            verdict, confidence, evidence = "REFUTED", 1.0-best_similarity, [f"Little support in {best_result['title'] if best_result else 'N/A'}"]
        return FactCheckResult(claim, "Wikipedia", confidence, verdict, evidence, best_result['title'] if best_result else None, best_similarity, datetime.now().isoformat())

    def fact_check_json(self, scraper_json: Dict[str, Any]) -> Dict[str, Any]:
        claims = self.extract_context_claims(scraper_json)
        results = [self.fact_check_claim(c).__dict__ for c in claims]
        total = len(results)
        supported = sum(1 for r in results if r['verdict']=="SUPPORTED")
        refuted = sum(1 for r in results if r['verdict']=="REFUTED")
        neutral = sum(1 for r in results if r['verdict']=="NEUTRAL")
        not_found = sum(1 for r in results if r['verdict']=="NOT_FOUND")
        avg_conf = sum(r['confidence'] for r in results)/total if total>0 else 0
        return {
            'fact_check_results': results,
            'statistics': {
                'total_claims': total,
                'supported': supported,
                'refuted': refuted,
                'neutral': neutral,
                'not_found': not_found,
                'average_confidence': avg_conf,
                'reliability_score': (supported/total if total>0 else 0)
            },
            'timestamp': datetime.now().isoformat()
        }

# -------------------- Script to analyze scraper_output.json --------------------
if __name__ == "__main__":
    SCRAPER_JSON = Path("scraper_output.json")
    OUTPUT_JSON = Path("wiki_fact_check_results.json")

    if not SCRAPER_JSON.exists():
        raise FileNotFoundError(f"{SCRAPER_JSON} not found.")

    with open(SCRAPER_JSON, "r", encoding="utf-8") as f:
        scraped_articles = json.load(f)

    if not isinstance(scraped_articles, dict):
        raise ValueError("Expected a dictionary of scraped articles in scraper_output.json")

    checker = ContextFactChecker()
    fact_check_results = {}

    for url, article in scraped_articles.items():
        try:
            result = checker.fact_check_json(article)
            fact_check_results[url] = result
        except Exception as e:
            fact_check_results[url] = {"error": str(e)}

    # Save results
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(fact_check_results, f, indent=2, ensure_ascii=False)

    print(f"Saved Wikipedia fact check results to {OUTPUT_JSON}")
