from serpapi import GoogleSearch

params = {
  "engine": "google_reverse_image",
  "image_url": "https://i.imgur.com/5bGzZi7.jpg",
  "api_key": "API_KEY"
}

search = GoogleSearch(params)
results = search.get_dict()
image_results = results["'image_results'"]
print(image_results[:3])