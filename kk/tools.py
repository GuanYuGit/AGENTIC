import os
from serpapi import GoogleSearch
from strands import tool
from dotenv import load_dotenv
import json

# Load environment variables from .env
load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")  # Make sure your .env has SERPAPI_KEY=your_key_here


@tool
def serpapi_search(image_url, max_results=5):
    """
    Perform a Google Reverse Image search via SerpAPI and return
    only the most relevant information for determining authenticity.
    
    Args:
        image_url (str): URL of the image to search.
        api_key (str): Your SerpAPI key.
        max_results (int): Number of top results to return.
    
    Returns:
        List[Dict]: Each dict contains the key info from image_results.
    """
    params = {
        "engine": "google_reverse_image",
        "image_url": image_url,
        "api_key": SERPAPI_KEY
    }

    search = GoogleSearch(params)
    results = search.get_dict()

    # Get the main image results
    image_results = results.get("image_results", [])

    # Extract only the authenticity-relevant fields
    output = []
    for res in image_results[:max_results]:
        output.append({
            "position": res.get("position"),
            "title": res.get("title"),
            "link": res.get("link"),
            "source": res.get("source"),
            "snippet": res.get("snippet"),
            "snippet_highlighted_words": res.get("snippet_highlighted_words")
        })

    return output

@tool
def sensity_check(image_url: str, api_key: str):
    """
    Placeholder Sensity tool for future use.
    """
    return {"status": "tool_not_available"}