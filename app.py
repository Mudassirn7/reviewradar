import streamlit as st
import requests
import json
import time
import re
import urllib.parse
import base64

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ReviewRadar — Lead Finder",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

* { font-family: 'Space Grotesk', sans-serif; }

.stApp {
    background: #0a0a0f;
    color: #e8e8f0;
}

/* Header */
.hero-title {
    font-size: 3rem;
    font-weight: 700;
    background: linear-gradient(135deg, #ff4d6d, #ff8800);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -1px;
    margin-bottom: 0.2rem;
}
.hero-sub {
    color: #666680;
    font-size: 1rem;
    font-weight: 400;
    margin-bottom: 2rem;
}

/* Lead card */
.lead-card {
    background: #13131f;
    border: 1px solid #22223a;
    border-radius: 14px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1rem;
    transition: border-color 0.2s;
}
.lead-card:hover { border-color: #ff4d6d55; }
.lead-name {
    font-size: 1.1rem;
    font-weight: 600;
    color: #ffffff;
    margin-bottom: 0.2rem;
}
.lead-meta {
    font-size: 0.82rem;
    color: #55556e;
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 0.6rem;
}
.wa-badge {
    display: inline-block;
    background: #25D36622;
    color: #25D366;
    border: 1px solid #25D36644;
    border-radius: 20px;
    padding: 2px 12px;
    font-size: 0.78rem;
    font-weight: 500;
}
.review-box {
    background: #0a0a0f;
    border-left: 3px solid #ff4d6d;
    border-radius: 0 8px 8px 0;
    padding: 0.8rem 1rem;
    margin-top: 0.8rem;
    font-size: 0.88rem;
    color: #aaaacc;
    font-style: italic;
}
.star-row { color: #ff4d6d; font-size: 0.9rem; margin-bottom: 0.3rem; }

/* Stats row */
.stat-box {
    background: #13131f;
    border: 1px solid #22223a;
    border-radius: 12px;
    padding: 1rem;
    text-align: center;
}
.stat-num { font-size: 2rem; font-weight: 700; color: #ff4d6d; }
.stat-label { font-size: 0.78rem; color: #555570; margin-top: 0.1rem; }

/* Button override */
div.stButton > button {
    background: linear-gradient(135deg, #ff4d6d, #ff8800);
    color: white;
    border: none;
    border-radius: 10px;
    padding: 0.6rem 2rem;
    font-weight: 600;
    font-size: 1rem;
    width: 100%;
    transition: opacity 0.2s;
}
div.stButton > button:hover { opacity: 0.85; }

/* Input overrides */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div {
    background: #0a0a0f !important;
    border: 1px solid #22223a !important;
    color: #e8e8f0 !important;
    border-radius: 8px !important;
}

/* Progress */
.progress-msg {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
    color: #666680;
    margin: 0.3rem 0;
}

/* Divider */
hr { border-color: #22223a; }
</style>
""", unsafe_allow_html=True)


# ─── Helpers ───────────────────────────────────────────────────────────────────

APIFY_TOKEN = st.secrets.get("APIFY_TOKEN", "")

def format_whatsapp_number(phone_str, country_choice):
    """Clean and format phone numbers dynamically based on user's target country selection."""
    if not phone_str:
        return None
        
    # Standard clean: pure digits extract karein
    clean_number = re.sub(r'\D', '', phone_str)
    
    # 1. Agar number '+' ya standard format ke sath pehle se hi international hai
    if phone_str.strip().startswith('+'):
        return clean_number

    # 2. Country specific local format processing
    if country_choice == "Pakistan 🇵🇰":
        if clean_number.startswith('03') and len(clean_number) == 11:
            return '92' + clean_number[1:]
        elif clean_number.startswith('3') and len(clean_number) == 10:
            return '92' + clean_number
            
    elif country_choice == "Switzerland 🇨🇭":
        if clean_number.startswith('0') and len(clean_number) == 10:
            return '41' + clean_number[1:]
            
    elif country_choice == "United Arab Emirates 🇦🇪":
        if clean_number.startswith('0') and len(clean_number) == 9:
            return '971' + clean_number[1:]

    # Agar koi filter match na ho par solid digits hon
    return clean_number if len(clean_number) >= 10 else None


def run_apify_scraper(city: str, business_type: str, max_results: int = 20) -> list:
    """Run Apify Google Maps scraper using your working original actor."""
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
        run_id = r.json()["data"]["id"]
        
        status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}"
        for _ in range(60):
            time.sleep(5)
            status_r = requests.get(status_url).json()
            status = status_r["data"]["status"]
            if status == "SUCCEEDED":
                break
            elif status in ["FAILED", "ABORTED"]:
                return []
        
        dataset_id = status_r["data"]["defaultDatasetId"]
        data_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={APIFY_TOKEN}"
        results = requests.get(data_url).json()
        return results
    except Exception as e:
        st.error(f"Apify error: {e}")
        return []


def filter_negative(businesses: list, max_rating: float) -> list:
    """Filter businesses with rating below threshold and having 1 or 2-star reviews."""
    filtered = []
    for b in businesses:
        rating = b.get("totalScore") or b.get("rating") or 5
        if float(rating) <= max_rating:
            reviews = b.get("reviews", [])
            negative_reviews = [r for r in reviews if r.get("stars") in [1, 2]]
            if negative_reviews:
                b["_oneStarReviews"] = negative_reviews
                filtered.append(b)
    return filtered


# ─── UI ────────────────────────────────────────────────────────────────────────

st.markdown('<div class="hero-title">ReviewRadar 🎯</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Find businesses with negative reviews — reach them instantly</div>', unsafe_allow_html=True)

with st.container():
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    with col1:
        city = st.text_input("City", placeholder="e.g. Zurich, Lahore, Dubai")
    with col2:
        biz_type = st.text_input("Business Type", placeholder="e.g. restaurants, salons, gyms")
    with col3:
        # Dynamic country selection box for targeted parsing
        country_select = st.selectbox("Target Country", ["Switzerland 🇨🇭", "Pakistan 🇵🇰", "United Arab Emirates 🇦🇪", "International / Other 🌍"])
    with col4:
        max_rating = st.number_input("Max Rating", min_value=1.0, max_value=5.0, value=3.5, step=0.5)

col_a, col_b = st.columns([1, 3])
with col_a:
    max_results = st.selectbox("Scan how many?", [10, 20, 30, 50], index=1)

st.markdown("---")

run_btn = st.button("🔍 Find Leads")

if run_btn:
    if not city or not biz_type:
        st.warning("Please enter city and business type.")
    elif not APIFY_TOKEN:
        st.error("Add APIFY_TOKEN in Streamlit Secrets.")
    else:
        progress = st.empty()
        progress.markdown('<div class="progress-msg">⟳ Scanning Google Maps via Apify...</div>', unsafe_allow_html=True)
        
        businesses = run_apify_scraper(city, biz_type, max_results)
        
        if not businesses:
            st.error("No data returned. Check Apify token or try again.")
            st.stop()
        
        progress.markdown('<div class="progress-msg">⟳ Filtering negative reviews...</div>', unsafe_allow_html=True)
        negatives = filter_negative(businesses, max_rating)
        
        if not negatives:
            st.warning("No businesses found with low ratings and bad reviews.")
            st.stop()
        
        leads = []
        
        for biz in negatives:
            phone = biz.get("phone", "")
            email = biz.get("email", "") or biz.get("emailId", "")
            name = biz.get("title", "Unknown")
            
            # Hybrid Outreach Check
            if not phone and not email:
                continue
                
            # Dynamic targeted country formatting call
            wa_number = format_whatsapp_number(phone, country_select)
            
            encoded_msg = urllib.parse.quote(f"Hi {name}, I noticed some negative reviews on your Google Maps profile. We can help you manage and clean fake reviews professionally. Let us know if you are interested!")
            wa_link = f"https://wa.me/{wa_number}?text={encoded_msg}" if wa_number else None
            mail_link = f"mailto:{email}?subject=Google Maps Review Management&body=Hi {name}," if email else None
            
            leads.append({
                "name": name,
                "phone": phone,
                "email": email,
                "address": biz.get("address", "N/A"),
                "rating": biz.get("totalScore") or biz.get("rating") or "?",
                "website": biz.get("website", ""),
                "reviews": biz["_oneStarReviews"][:3],
                "wa_link": wa_link,
                "mail_link": mail_link
            })
        
        progress.empty()
        
        if not leads:
            st.warning("Businesses found but none had valid contact fields (Phone/Email).")
            st.stop()
        
        # Stats Display
        s1, s2, s3 = st.columns(3)
        with s1:
            st.markdown(f'<div class="stat-box"><div class="stat-num">{len(businesses)}</div><div class="stat-label">Businesses Scanned</div></div>', unsafe_allow_html=True)
        with s2:
            st.markdown(f'<div class="stat-box"><div class="stat-num">{len(negatives)}</div><div class="stat-label">Low Rating Found</div></div>', unsafe_allow_html=True)
        with s3:
            st.markdown(f'<div class="stat-box"><div class="stat-num">{len(leads)}</div><div class="stat-label">Active Leads Generated</div></div>', unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### ✅ Your Leads")
        
        for lead in leads:
            with st.container():
                badges_html = ""
                if lead['wa_link']:
                    badges_html += '<span class="wa-badge" style="margin-right: 5px;">✓ WhatsApp Ready</span>'
                if lead['email']:
                    badges_html += '<span class="wa-badge" style="background:#00b4d822; color:#00b4d8; border:1px solid #00b4d844;">✓ Email Available</span>'
                
                st.markdown(f"""
                <div class="lead-card">
                    <div class="lead-name">{lead['name']}</div>
                    <div class="lead-meta">📍 {lead['address']} &nbsp;|&nbsp; ⭐ {lead['rating']}</div>
                    <div style="font-size:0.85rem; color:#aaaacc; margin-bottom:8px;">📞 Phone: {lead['phone'] if lead['phone'] else 'N/A'} &nbsp;|&nbsp; 📧 Email: {lead['email'] if lead['email'] else 'N/A'}</div>
                    {badges_html}
                    {'<br><small style="color:#555570; margin-top:5px; display:block;">🌐 ' + lead['website'] + '</small>' if lead['website'] else ''}
                </div>
                """, unsafe_allow_html=True)
                
                # Expandable reviews area
                with st.expander(f"📋 View Negative Reviews ({len(lead['reviews'])})"):
                    for rev in lead["reviews"]:
                        st.markdown(f"""
                        <div class="review-box">
                            <div class="star-row">★☆☆☆☆ — {rev.get('reviewer', {}).get('name', 'Anonymous')}</div>
                            "{rev.get('text', 'No text comment left.')}"
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Dynamic Image rendering straight from JSON
                        imgs = rev.get("photos", []) or rev.get("images", []) or rev.get("reviewImageUrls", [])
                        if imgs:
                            img_cols = st.columns(min(len(imgs), 3))
                            for idx, img in enumerate(imgs[:3]):
                                img_url = img if isinstance(img, str) else (img.get("imageUrl") or img.get("url", ""))
                                if img_url:
                                    with img_cols[idx]:
                                        st.image(img_url, width=180)
                
                # Action Buttons
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if lead["wa_link"]:
                        st.link_button(f"💬 WhatsApp {lead['name']}", lead["wa_link"])
                    else:
                        st.button(f"❌ No WhatsApp Available", disabled=True, key=f"no_wa_{lead['name']}")
                        
                with btn_col2:
                    if lead["mail_link"]:
                        st.link_button(f"✉️ Email {lead['name']}", lead["mail_link"])
                    else:
                        st.button(f"❌ No Email Available", disabled=True, key=f"no_mail_{lead['name']}")
                        
                st.markdown("---")
