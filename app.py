import streamlit as st
import requests
import time
import re
from playwright.sync_api import sync_playwright
import base64

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ReviewRadar — Lead Finder",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
* { font-family: 'Space Grotesk', sans-serif; }
.stApp { background: #0a0a0f; color: #e8e8f0; }
.hero-title {
    font-size: 3rem; font-weight: 700;
    background: linear-gradient(135deg, #ff4d6d, #ff8800);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    letter-spacing: -1px; margin-bottom: 0.2rem;
}
.hero-sub { color: #666680; font-size: 1rem; margin-bottom: 2rem; }
.lead-card {
    background: #13131f; border: 1px solid #22223a; border-radius: 14px;
    padding: 1.4rem 1.6rem; margin-bottom: 1rem;
}
.lead-card:hover { border-color: #ff4d6d55; }
.lead-name { font-size: 1.1rem; font-weight: 600; color: #ffffff; margin-bottom: 0.2rem; }
.lead-meta { font-size: 0.82rem; color: #55556e; font-family: 'JetBrains Mono', monospace; margin-bottom: 0.6rem; }
.wa-badge {
    display: inline-block; background: #25D36622; color: #25D366;
    border: 1px solid #25D36644; border-radius: 20px; padding: 2px 12px;
    font-size: 0.78rem; font-weight: 500; margin-right: 6px;
}
.email-badge {
    display: inline-block; background: #4A90E222; color: #4A90E2;
    border: 1px solid #4A90E244; border-radius: 20px; padding: 2px 12px;
    font-size: 0.78rem; font-weight: 500; margin-right: 6px;
}
.skip-badge {
    display: inline-block; background: #ff4d6d22; color: #ff4d6d;
    border: 1px solid #ff4d6d44; border-radius: 20px; padding: 2px 12px;
    font-size: 0.78rem; font-weight: 500;
}
.review-box {
    background: #0a0a0f; border-left: 3px solid #ff4d6d;
    border-radius: 0 8px 8px 0; padding: 0.8rem 1rem; margin-top: 0.8rem;
    font-size: 0.88rem; color: #aaaacc; font-style: italic;
}
.star-row { color: #ff4d6d; font-size: 0.9rem; margin-bottom: 0.3rem; }
.stat-box { background: #13131f; border: 1px solid #22223a; border-radius: 12px; padding: 1rem; text-align: center; }
.stat-num { font-size: 2rem; font-weight: 700; color: #ff4d6d; }
.stat-label { font-size: 0.78rem; color: #555570; margin-top: 0.1rem; }
div.stButton > button {
    background: linear-gradient(135deg, #ff4d6d, #ff8800);
    color: white; border: none; border-radius: 10px;
    padding: 0.6rem 2rem; font-weight: 600; font-size: 1rem;
    width: 100%; transition: opacity 0.2s;
}
div.stButton > button:hover { opacity: 0.85; }
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div {
    background: #0a0a0f !important; border: 1px solid #22223a !important;
    color: #e8e8f0 !important; border-radius: 8px !important;
}
.progress-msg { font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; color: #666680; margin: 0.3rem 0; }
hr { border-color: #22223a; }
</style>
""", unsafe_allow_html=True)

# ─── Country Config ─────────────────────────────────────────────────────────────
COUNTRIES = {
    "🇺🇸 USA (+1)":          {"code": "1",  "len": [10]},
    "🇨🇦 Canada (+1)":       {"code": "1",  "len": [10]},
    "🇬🇧 UK (+44)":          {"code": "44", "len": [10]},
    "🇩🇪 Germany (+49)":     {"code": "49", "len": [10, 11]},
    "🇫🇷 France (+33)":      {"code": "33", "len": [9]},
    "🇨🇭 Switzerland (+41)": {"code": "41", "len": [9]},
    "🇳🇱 Netherlands (+31)": {"code": "31", "len": [9]},
    "🇸🇪 Sweden (+46)":      {"code": "46", "len": [9]},
    "🇳🇴 Norway (+47)":      {"code": "47", "len": [8]},
    "🇩🇰 Denmark (+45)":     {"code": "45", "len": [8]},
    "🇦🇺 Australia (+61)":   {"code": "61", "len": [9]},
}

def normalize_phone(phone: str, country_code: str) -> str:
    """Strip formatting and ensure country code is present."""
    digits = re.sub(r'[^\d]', '', phone)
    # Remove leading zeros
    digits = digits.lstrip('0')
    # If already starts with country code, keep it
    if digits.startswith(country_code):
        return digits
    # If starts with +countrycode (already stripped +)
    return country_code + digits

def check_whatsapp(phone: str, country_code: str) -> bool:
    """Check if number has WhatsApp."""
    try:
        normalized = normalize_phone(phone, country_code)
        if len(normalized) < 7:
            return False
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"https://wa.me/{normalized}", timeout=15000)
            page.wait_for_timeout(3000)
            content = page.content().lower()
            browser.close()
            return "continue" in content or "open whatsapp" in content
    except Exception:
        return False

def take_review_screenshot(place_name: str, review_text: str) -> str | None:
    """Screenshot of 1-star review card."""
    try:
        html = f"""<html><head><style>
        body {{ margin:0; background:#0a0a0f; display:flex; align-items:center; justify-content:center; min-height:100vh; }}
        .card {{ background:#13131f; border:1px solid #22223a; border-radius:16px; padding:28px 32px; max-width:520px; width:100%; font-family:'Segoe UI',sans-serif; }}
        .biz {{ font-size:14px; color:#666680; margin-bottom:6px; }}
        .bar {{ width:40px; height:3px; background:linear-gradient(90deg,#ff4d6d,#ff8800); border-radius:2px; margin-bottom:14px; }}
        .stars {{ color:#ff4d6d; font-size:18px; margin-bottom:10px; }}
        .review {{ font-size:15px; color:#ccccdd; line-height:1.6; font-style:italic; }}
        </style></head>
        <body><div class="card">
            <div class="biz">{place_name}</div>
            <div class="bar"></div>
            <div class="stars">★ 1-Star Review</div>
            <div class="review">"{review_text[:300]}{'...' if len(review_text) > 300 else ''}"</div>
        </div></body></html>"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 600, "height": 400})
            page.set_content(html)
            page.wait_for_timeout(500)
            shot = page.screenshot(full_page=True)
            browser.close()
        return base64.b64encode(shot).decode()
    except Exception:
        return None

def run_apify_scraper(city: str, business_type: str, max_results: int) -> list:
    """Run Apify Google Maps scraper."""
    APIFY_TOKEN = st.secrets.get("APIFY_TOKEN", "")
    url = f"https://api.apify.com/v2/acts/compass~crawler-google-places/runs?token={APIFY_TOKEN}"
    payload = {
        "searchStringsArray": [f"{business_type} in {city}"],
        "maxCrawledPlaces": max_results,
        "language": "en",
        "maxReviews": 10,
        "reviewsSort": "newest",
        "scrapeReviewerName": True,
        "includeImages": True,
    }
    try:
        r = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
        run_id = r.json()["data"]["id"]
        status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}"
        status_r = {}
        for _ in range(60):
            time.sleep(5)
            status_r = requests.get(status_url).json()
            status = status_r["data"]["status"]
            if status == "SUCCEEDED":
                break
            elif status in ["FAILED", "ABORTED"]:
                return []
        dataset_id = status_r["data"]["defaultDatasetId"]
        return requests.get(f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={APIFY_TOKEN}").json()
    except Exception as e:
        st.error(f"Apify error: {e}")
        return []

def filter_negative(businesses: list, max_rating: float) -> list:
    filtered = []
    for b in businesses:
        rating = float(b.get("totalScore") or b.get("rating") or 5)
        if rating <= max_rating:
            one_star = [r for r in b.get("reviews", []) if r.get("stars") == 1]
            if one_star:
                b["_oneStarReviews"] = one_star
                filtered.append(b)
    return filtered

# ─── UI ────────────────────────────────────────────────────────────────────────
st.markdown('<div class="hero-title">ReviewRadar 🎯</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Find businesses with negative reviews — reach them via WhatsApp & Email</div>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns([2, 2, 1.5, 1])
with col1:
    city = st.text_input("City", placeholder="e.g. New York, London, Zurich")
with col2:
    biz_type = st.text_input("Business Type", placeholder="e.g. restaurants, salons, gyms")
with col3:
    country_sel = st.selectbox("Country", list(COUNTRIES.keys()))
with col4:
    max_rating = st.number_input("Max Rating", min_value=1.0, max_value=3.0, value=2.5, step=0.5)

col_a, _ = st.columns([1, 3])
with col_a:
    max_results = st.selectbox("Scan how many?", [10, 20, 30, 50], index=1)

st.markdown("---")
run_btn = st.button("🔍 Find Leads")

if run_btn:
    if not city or not biz_type:
        st.warning("Please enter city and business type.")
    elif not st.secrets.get("APIFY_TOKEN", ""):
        st.error("Add APIFY_TOKEN in Streamlit Secrets.")
    else:
        country_code = COUNTRIES[country_sel]["code"]
        progress = st.empty()
        log = st.empty()

        # Step 1: Scrape
        progress.markdown('<div class="progress-msg">⟳ Scanning Google Maps...</div>', unsafe_allow_html=True)
        businesses = run_apify_scraper(city, biz_type, max_results)
        if not businesses:
            st.error("No data returned. Check Apify token or try again.")
            st.stop()

        # Step 2: Filter
        progress.markdown('<div class="progress-msg">⟳ Filtering negative reviews...</div>', unsafe_allow_html=True)
        negatives = filter_negative(businesses, max_rating)
        if not negatives:
            st.warning("No businesses found with low ratings and 1-star reviews.")
            st.stop()

        # Step 3: Contact check (WhatsApp first, then email)
        leads = []
        for i, biz in enumerate(negatives):
            phone = biz.get("phone", "")
            email = biz.get("email", "") or biz.get("emails", [""])[0] if biz.get("emails") else ""
            name  = biz.get("title", "Unknown")

            log.markdown(f'<div class="progress-msg">🔍 Checking {i+1}/{len(negatives)}: {name}</div>', unsafe_allow_html=True)

            has_wa    = False
            has_email = bool(email and "@" in email)

            # WhatsApp check
            if phone:
                progress.markdown('<div class="progress-msg">📱 Checking WhatsApp...</div>', unsafe_allow_html=True)
                has_wa = check_whatsapp(phone, country_code)

            # Skip if no contact at all
            if not has_wa and not has_email:
                continue

            # Screenshot
            progress.markdown('<div class="progress-msg">📸 Taking review screenshot...</div>', unsafe_allow_html=True)
            top_review   = biz["_oneStarReviews"][0]
            review_text  = top_review.get("text", "No review text.")
            screenshot   = take_review_screenshot(name, review_text)

            normalized_phone = normalize_phone(phone, country_code) if phone else ""

            leads.append({
                "name":     name,
                "phone":    phone,
                "email":    email,
                "address":  biz.get("address", "N/A"),
                "rating":   biz.get("totalScore", "?"),
                "website":  biz.get("website", ""),
                "reviews":  biz["_oneStarReviews"][:3],
                "screenshot": screenshot,
                "has_wa":   has_wa,
                "has_email": has_email,
                "wa_link":  f"https://wa.me/{normalized_phone}" if has_wa else "",
            })

        log.empty()
        progress.empty()

        if not leads:
            st.warning("No contactable businesses found. Try different city/type.")
            st.stop()

        # Stats
        wa_only    = sum(1 for l in leads if l["has_wa"] and not l["has_email"])
        email_only = sum(1 for l in leads if l["has_email"] and not l["has_wa"])
        both       = sum(1 for l in leads if l["has_wa"] and l["has_email"])

        s1, s2, s3, s4 = st.columns(4)
        with s1:
            st.markdown(f'<div class="stat-box"><div class="stat-num">{len(businesses)}</div><div class="stat-label">Scanned</div></div>', unsafe_allow_html=True)
        with s2:
            st.markdown(f'<div class="stat-box"><div class="stat-num">{len(leads)}</div><div class="stat-label">Total Leads</div></div>', unsafe_allow_html=True)
        with s3:
            st.markdown(f'<div class="stat-box"><div class="stat-num">{both + wa_only}</div><div class="stat-label">WhatsApp</div></div>', unsafe_allow_html=True)
        with s4:
            st.markdown(f'<div class="stat-box"><div class="stat-num">{both + email_only}</div><div class="stat-label">Email</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### ✅ Your Leads")

        for lead in leads:
            # Build badges
            badges = ""
            if lead["has_wa"]:
                badges += '<span class="wa-badge">✓ WhatsApp</span>'
            if lead["has_email"]:
                badges += '<span class="email-badge">✉ Email</span>'

            st.markdown(f"""
            <div class="lead-card">
                <div class="lead-name">{lead['name']}</div>
                <div class="lead-meta">📍 {lead['address']} &nbsp;|&nbsp; ⭐ {lead['rating']} &nbsp;|&nbsp; 📞 {lead['phone'] or 'N/A'}</div>
                {badges}
                {'<br><small style="color:#555570;margin-top:4px;display:block">🌐 ' + lead['website'] + '</small>' if lead['website'] else ''}
                {'<br><small style="color:#4A90E2;margin-top:4px;display:block">📧 ' + lead['email'] + '</small>' if lead['email'] else ''}
            </div>
            """, unsafe_allow_html=True)

            # Reviews expander
            with st.expander(f"📋 1-Star Reviews ({len(lead['reviews'])})"):
                for rev in lead["reviews"]:
                    st.markdown(f"""
                    <div class="review-box">
                        <div class="star-row">★☆☆☆☆ — {rev.get('reviewer', {}).get('name', 'Anonymous')}</div>
                        {rev.get('text', 'No text.')}
                    </div>
                    """, unsafe_allow_html=True)
                    imgs = rev.get("photos", []) or rev.get("images", [])
                    if imgs:
                        img_cols = st.columns(min(len(imgs), 3))
                        for idx, img in enumerate(imgs[:3]):
                            img_url = img.get("imageUrl") or img.get("url", "")
                            if img_url:
                                with img_cols[idx]:
                                    st.image(img_url, width=180)

            # Screenshot expander
            if lead["screenshot"]:
                with st.expander("🖼️ Review Screenshot"):
                    img_bytes = base64.b64decode(lead["screenshot"])
                    st.image(img_bytes, use_container_width=True)
                    st.download_button(
                        "⬇ Download Screenshot",
                        data=img_bytes,
                        file_name=f"{lead['name'].replace(' ','_')}_review.png",
                        mime="image/png",
                        key=f"dl_{lead['name']}"
                    )

            # Action buttons
            btn_cols = st.columns(2)
            with btn_cols[0]:
                if lead["has_wa"]:
                    st.link_button(f"💬 WhatsApp", lead["wa_link"])
            with btn_cols[1]:
                if lead["has_email"]:
                    st.link_button(f"📧 Email", f"mailto:{lead['email']}")

            st.markdown("---")
