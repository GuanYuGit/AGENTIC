import os
import requests
import concurrent.futures
from serpapi import GoogleSearch
from strands import tool
from dotenv import load_dotenv

# Load environment variables from .env (if it exists)
load_dotenv(override=False)

SERPAPI_KEY = os.getenv("SERPAPI_KEY")  # Make sure your .env has SERPAPI_KEY=your_key_here


@tool
def serpapi_search(image_url, max_results=3, timeout=8):
    """
    Perform a Google Reverse Image search via SerpAPI and return only the
    most relevant information for determining authenticity.
    
    Args:
        image_url (str): URL of the image to search.
        max_results (int): Number of top results to return.
        timeout (int): Max time (in seconds) to wait for the SerpAPI response.
    
    Returns:
        List[Dict]: Each dict contains key info from image_results.
    """
    # Skip SVGs immediately
    if image_url.lower().endswith(".svg"):
        return [{
            "image_url": image_url,
            "tools_called": ["serpapi_search"],
            "tool_results": {"serpapi_search": {"error": "Skipped: SVG images cannot be reverse searched"}},
            "assessment": 0.5,
            "evidence": "The image is an SVG file, which cannot be reverse searched. "
        }]

    # Define a helper to actually call SerpAPI
    def _call_serpapi():
        search = GoogleSearch({
            "engine": "google_reverse_image",
            "image_url": image_url,
            "api_key": SERPAPI_KEY
        })
        return search.get_dict()

    try:
        # Use a thread with timeout to avoid hanging
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_call_serpapi)
            results = future.result(timeout=timeout)

        # Safely extract image results
        image_results = results.get("image_results", [])
        if not isinstance(image_results, list):
            image_results = []

        # Fall back to image_sizes if no image_results
        if not image_results:
            image_results = results.get("image_sizes", [])
            if not isinstance(image_results, list):
                image_results = []

        if not image_results:
            return [{
                "image_url": image_url,
                "tools_called": ["serpapi_search"],
                "tool_results": {"serpapi_search": {"error": "No results found"}},
                "assessment": 0.5,
                "evidence": "The reverse image search returned no results. More information is needed."
            }]

        # Extract only fields relevant for your output
        output = []
        for res in image_results[:max_results]:
            output.append({
                "image_url": image_url,
                "tools_called": ["serpapi_search"],
                "tool_results": {
                    "serpapi_search": {
                        "position": res.get("position"),
                        "title": res.get("title"),
                        "link": res.get("link"),
                        "source": res.get("source"),
                        "snippet": res.get("snippet"),
                        "snippet_highlighted_words": res.get("snippet_highlighted_words")
                    }
                },
                "assessment": 0.5 if "position" not in res else 0.9,
                "evidence": "Reverse image search results obtained." if "position" in res else "Partial results obtained."
            })

        return output

    except concurrent.futures.TimeoutError:
        return [{
            "image_url": image_url,
            "tools_called": ["serpapi_search"],
            "tool_results": {"serpapi_search": {"error": "Timeout: search took too long"}},
            "assessment": 0.5,
            "evidence": "The reverse image search timed out. More information is needed."
        }]
    except Exception as e:
        return [{
            "image_url": image_url,
            "tools_called": ["serpapi_search"],
            "tool_results": {"serpapi_search": {"error": f"Unexpected error: {str(e)}"}},
            "assessment": 0.5,
            "evidence": "The reverse image search was unsuccessful due to an unexpected error. More information is needed."
        }]
