def run_apify_scraper(city: str, business_type: str, max_results: int = 20) -> list:
    """Run Apify Google Maps scraper using your working original actor with safety checks."""
    url = f"https://api.apify.com/v2/acts/compass~crawler-google-places/runs?token={APIFY_TOKEN}"
    
    payload = {
        "searchStringsArray": [f"{business_type} in {city}"],
        "maxCrawledPlaces": max_results,
        "language": "en",
        "maxReviews": 10,
        "reviewsSort": "newest",
        "scrapeReviewerName": True,
        "scrapeReviewerId": False,
        "scrapeReviewerUrl": False,
        "scrapeReviewsPersonalData": False,
        "includeImages": True,
    }
    
    headers = {"Content-Type": "application/json"}
    
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        response_json = r.json()
        
        # Check if 'data' is present in response
        if "data" not in response_json:
            st.error(f"❌ Apify Authentication/Actor Error: {response_json.get('message', response_json)}")
            return []
            
        run_id = response_json["data"]["id"]
        
        status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}"
        for _ in range(60):
            time.sleep(5)
            status_r = requests.get(status_url).json()
            status = status_r["data"]["status"]
            if status == "SUCCEEDED":
                break
            elif status in ["FAILED", "ABORTED"]:
                st.error(f"❌ Actor Run {status} on Apify Cloud.")
                return []
        
        dataset_id = status_r["data"]["defaultDatasetId"]
        data_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={APIFY_TOKEN}"
        results = requests.get(data_url).json()
        return results
    except Exception as e:
        st.error(f"Apify Connection Error: {e}")
        return []
