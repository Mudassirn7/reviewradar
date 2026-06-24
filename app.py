import streamlit as st
from apify_client import ApifyClient
import urllib.parse
import re

# Page configuration
st.set_page_config(page_title="ReviewRadar 🎯", page_icon="🎯", layout="wide")

st.title("ReviewRadar — Lead Generation Tool 🎯")
st.caption("Find businesses with negative reviews and instantly contact them.")

# Sidebar Inputs
st.sidebar.header("Search Parameters")
city = st.sidebar.text_input("City Name", value="Lahore")
business_type = st.sidebar.text_input("Business Type", value="Restaurants")
max_rating = st.sidebar.slider("Maximum Rating Filter", 1.0, 5.0, 3.5, step=0.1)

# Get API Token securely from Streamlit Secrets
try:
    apify_token = st.secrets["APIFY_TOKEN"]
    client = ApifyClient(apify_token)
except Exception:
    st.error("❌ APIFY_TOKEN missing! Please add it in Streamlit Secrets.")
    st.stop()

# Helper function to clean and format pakistani/international numbers for WhatsApp
def format_whatsapp_number(phone_str):
    if not phone_str:
        return None
    # Sirf digits (numbers) extract karein
    clean_number = re.sub(r'\D', '', phone_str)
    
    # Agar number 03 se shuru ho raha hai (Local Pak number), toh 0 hata kar 92 lagayein
    if clean_number.startswith('03') and len(clean_number) == 11:
        clean_number = '92' + clean_number[1:]
    elif clean_number.startswith('3') and len(clean_number) == 10:
        clean_number = '92' + clean_number
        
    return clean_number if len(clean_number) >= 10 else None

if st.sidebar.button("Start Finding Leads 🚀"):
    search_query = f"{business_type} in {city}"
    st.info(f"🔍 Searching for '{search_query}' via Apify...")
    
    with st.spinner("Fetching data from Google Maps..."):
        try:
            run_input = {
                "searchQueries": [search_query],
                "maxCrawledPlacesPerSearch": 20, # Checked numbers properly
                "includeReviews": True,
                "language": "en"
            }
            run = client.actor("komorand/google-maps-scraper").call(run_input=run_input)
            dataset_items = list(client.dataset(run["defaultDatasetId"]).list_items().items)
        except Exception as e:
            st.error(f"Apify Fetch Error: {e}")
            st.stop()

    if not dataset_items:
        st.warning("No businesses found for this search.")
    else:
        valid_leads_found = 0
        
        for item in dataset_items:
            name = item.get("title", "N/A")
            phone = item.get("phone", "")
            email = item.get("email", "")
            rating = item.get("totalScore", 5.0)
            reviews = item.get("reviews", [])
            
            # Agar na phone hai na email, toh skip karein
            if not phone and not email:
                continue
                
            # Filter by rating
            if rating > max_rating:
                continue

            # Check for negative reviews (1 or 2 stars)
            negative_reviews = [r for r in reviews if r.get("stars") in [1, 2]]
            if not negative_reviews:
                continue 

            # Format phone for WhatsApp
            wa_number = format_whatsapp_number(phone)
            
            valid_leads_found += 1

            # Display Lead
            with st.container():
                st.markdown("---")
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.subheader(f"🏢 {name}")
                    st.write(f"⭐️ **Rating:** {rating} / 5.0")
                    if phone: st.write(f"📞 **Phone:** {phone} (Formatted: `{wa_number}`)")
                    if email: st.write(f"📧 **Email:** {email}")
                
                with col2:
                    st.markdown("### ⚡ Quick Outreach")
                    if wa_number:
                        encoded_msg = urllib.parse.quote(f"Hi {name}, I noticed some negative reviews on your Google Maps profile. We can help you manage and remove fake reviews professionally. Let us know if you are interested!")
                        wa_link = f"https://wa.me/{wa_number}?text={encoded_msg}"
                        st.markdown(f"[💬 Open WhatsApp Chat]({wa_link})")
                    else:
                        st.caption("⚠️ No valid WhatsApp number format")
                    
                    if email:
                        mail_link = f"mailto:{email}?subject=Google Maps Review Management&body=Hi {name},"
                        st.markdown(f"[✉️ Send Email Directly]({mail_link})")

                # Show negative reviews
                st.markdown("**🚨 Negative Feedback:**")
                for rev in negative_reviews[:2]:
                    text_content = rev.get("text", "No text comment left.")
                    st.error(f"💬 \"{text_content}\" — {rev.get('stars')} ⭐️")
                    
                    review_images = rev.get("reviewImageUrls", [])
                    if review_images:
                        st.image(review_images[0], caption="Attached Review Image", width=300)

        if valid_leads_found == 0:
            st.info("💡 Filter criteria matched 0 businesses. Try increasing 'Maximum Rating Filter' or searching a different area.")
        else:
            st.success(f"🎯 Displayed {valid_leads_found} potential leads successfully!")
