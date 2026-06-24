def run_apify_scraper(city: str, business_type: str, max_results: int = 20) -> list:
    """Run Apify Google Maps scraper using the reliable official ApifyClient."""
    from apify_client import ApifyClient
    
    # Initialize the client securely
    client = ApifyClient(APIFY_TOKEN)
    search_query = f"{business_type} in {city}"
    
    # Actor configuration exactly matching your working actor
    run_input = {
        "searchStringsArray": [search_query],
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
    
    try:
        # Live status check on screen
        status_placeholder = st.empty()
        status_placeholder.markdown('<div class="progress-msg">⏳ Sending request to Apify Cloud...</div>', unsafe_allow_html=True)
        
        # Start the actor run via official client
        run = client.actor("compass~crawler-google-places").call(run_input=run_input)
        
        status_placeholder.markdown('<div class="progress-msg">🚀 Fetching extracted dataset items...</div>', unsafe_allow_html=True)
        
        # Fetch data items directly from the resulting dataset
        dataset_items = list(client.dataset(run["defaultDatasetId"]).list_items().items)
        
        status_placeholder.empty() # Clear tracking text once done
        return dataset_items
        
    except Exception as e:
        st.error(f"❌ Apify Client Execution Error: {e}")
        return []
