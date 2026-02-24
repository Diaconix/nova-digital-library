import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client
import qrcode
from io import BytesIO
import os

# --- 1. CONFIG & BRANDING ---
st.set_page_config(page_title="Nova Digital Library", page_icon="assets/favicon.png", layout="wide")

# CSS BLOCK (No 'f' prefix here to avoid SyntaxError)
st.markdown("""
    <style>
    /* Global Corporate Styling - Adaptive */
    .stApp {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    div.stButton > button {
        border-radius: 20px;
    }
    .aicon-watermark {
        position: fixed;
        bottom: 10px;
        right: 15px;
        font-size: 11px;
        color: #888888;
        font-family: monospace;
        z-index: 9999;
        user-select: none;
    }
    
    /* MOBILE FIX 1: The Force-Wrap CSS Grid */
    @media (max-width: 768px) {
        [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
            gap: 2% !important; 
        }
        div[data-testid="column"] {
            width: 48% !important;
            flex: 0 0 48% !important;
            min-width: 48% !important;
            margin-bottom: 1rem !important; 
        }
    }
    
    /* MOBILE FIX 2: Glassmorphism Floating Cart (50% Transparency) */
    .floating-cart {
        position: fixed;
        bottom: 30px;
        left: 50%;
        transform: translateX(-50%);
        width: 90%;
        max-width: 400px;
        
        background: rgba(255, 255, 255, 0.5);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        
        border: 1px solid rgba(91, 33, 182, 0.3); 
        border-radius: 15px;
        padding: 15px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.15);
        z-index: 9998;
        text-align: center;
    }
    
    @media (prefers-color-scheme: dark) {
        .floating-cart {
            background: rgba(14, 17, 23, 0.5); 
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
    }
    
    .checkout-btn {
        display: block;
        margin-top: 10px;
        background-color: #5B21B6;
        color: white !important;
        padding: 12px;
        border-radius: 8px;
        text-decoration: none;
        font-weight: bold;
    }
    </style>
    <div class="aicon-watermark">Engineered by AICON Systems | calnwogu@gmail.com</div>
    """, unsafe_allow_html=True)

# --- 2. INITIALIZATION & SESSION STATE ---
try:
    SUPABASE_URL = st.secrets["supabase"]["url"]
    SUPABASE_KEY = st.secrets["supabase"]["key"]
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except KeyError:
    st.error("🚨 Secrets Error: Could not find [supabase] credentials in .streamlit/secrets.toml")
    st.stop()

if 'cart' not in st.session_state:
    st.session_state.cart = []
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

def get_qr(book_id):
    qr_url = f"https://aicon-library.streamlit.app/?id={book_id}"
    qr = qrcode.make(qr_url)
    buf = BytesIO()
    qr.save(buf, format="PNG")
    return buf.getvalue()

def get_rental_price(book_data):
    return 1500  

# ==========================================
# 🚦 TRAFFIC CONTROLLER (DYNAMIC ROUTING)
# ==========================================
query_params = st.query_params
scanned_book_id = query_params.get("id")
is_checkout_mode = query_params.get("checkout") == "true"

checkout_ids = []
if scanned_book_id:
    checkout_ids = [scanned_book_id]
elif is_checkout_mode and st.session_state.cart:
    checkout_ids = st.session_state.cart

if checkout_ids:
    # ---------------------------------------------------------
    # ROUTE A: EXPRESS CHECKOUT 
    # ---------------------------------------------------------
    st.markdown("## 📱 Nova Secure Checkout")
    
    try:
        res = supabase.table("lib_inventory").select("*").in_("id", checkout_ids).execute()
        
        if res.data:
            books = res.data
            total_price = sum(get_rental_price(b) for b in books)
            selar_link = "https://selar.com/d20is52cl1" 
            
            with st.container(border=True):
                st.markdown("### 🛒 Your Selection")
                for b in books:
                    st.markdown(f"- **{b['title']}** - ₦{get_rental_price(b):,.2f}")
                st.markdown(f"#### **Total Amount: ₦{total_price:,.2f}**")
            
            unavailable_books = [b['title'] for b in books if b['status'] != "Available"]
            if unavailable_books:
                st.error(f"🚨 Cannot proceed. The following books are no longer available: {', '.join(unavailable_books)}")
            else:
                st.markdown("### Choose Your Delivery Method")
                rental_method = st.radio(
                    "Delivery Options:", 
                    ["🚶 Standard (Library Pickup)", "🚚 Elite Member (Home Delivery)"],
                    label_visibility="collapsed"
                )
                
                if "Elite" in rental_method:
                    st.info("Your Elite Membership covers delivery fees! Verify your email to dispatch.")
                    member_email = st.text_input("Registered Elite Email").strip().lower()
                    
                    if st.button("Verify & Generate Payment Link", type="primary", use_container_width=True):
                        if member_email:
                            member_check = supabase.table("lib_members").select("*").eq("email", member_email).execute()
                            if member_check.data:
                                member = member_check.data[0]
                                for b in books:
                                    pending_rental = {
                                        "book_id": b['id'],
                                        "member_id": member['id'],
                                        "due_date": (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'),
                                        "delivery_type": "Home Delivery",
                                        "delivery_status": "Pending Verification",
                                        "is_paid": False
                                    }
                                    supabase.table("lib_rentals").insert(pending_rental).execute()
                                    supabase.table("lib_inventory").update({"status": "Reserved"}).eq("id", b['id']).execute()
                                
                                st.session_state.cart = []
                                st.success(f"Verified, {member['full_name']}! Ledger updated.")
                                st.info(f"⚠️ Note: Please adjust the quantity to **{len(books)}** on the Selar checkout page to total ₦{total_price:,.2f}.")
                                st.markdown(f'<a href="{selar_link}" target="_blank"><button style="width:100%; background-color:#5B21B6; color:white; padding:14px; border:none; border-radius:8px; font-weight:bold; cursor:pointer;">💳 Pay ₦{total_price:,.2f} via Selar</button></a>', unsafe_allow_html=True)
                            else:
                                st.error("Email not found. Are you registered for the Elite tier?")
                        else:
                            st.warning("Please enter your email.")
                else:
                    st.info("Standard rentals must be picked up physically from the library desk.")
                    guest_name = st.text_input("Enter your Name (for pickup reservation)")
                    
                    if st.button("Reserve & Generate Payment Link", type="primary", use_container_width=True):
                        if guest_name:
                            for b in books:
                                pending_rental = {
                                    "book_id": b['id'],
                                    "due_date": (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'),
                                    "delivery_type": f"Pickup by {guest_name}",
                                    "delivery_status": "Awaiting Pickup",
                                    "is_paid": False
                                }
                                supabase.table("lib_rentals").insert(pending_rental).execute()
                                supabase.table("lib_inventory").update({"status": "Reserved"}).eq("id", b['id']).execute()
                            
                            st.session_state.cart = []
                            st.success("Reservation logged! Books are secured for you.")
                            st.info(f"⚠️ Note: Please adjust the quantity to **{len(books)}** on the Selar checkout page to total ₦{total_price:,.2f}.")
                            st.markdown(f'<a href="{selar_link}" target="_blank"><button style="width:100%; background-color:#5B21B6; color:white; padding:14px; border:none; border-radius:8px; font-weight:bold; cursor:pointer;">💳 Pay ₦{total_price:,.2f} via Selar</button></a>', unsafe_allow_html=True)
                        else:
                            st.warning("Please provide a name for the pickup reservation.")
            
            st.divider()
            if st.button("← Back to Main Library", use_container_width=True):
                st.query_params.clear()
                st.rerun()
        else:
            st.error("🚨 Book(s) not found.")
    except Exception as e:
        st.error(f"Database connection error: {e}")

else:
    # ---------------------------------------------------------
    # ROUTE B: THE DASHBOARD TABS 
    # ---------------------------------------------------------
    
    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        st.sidebar.image(logo_path, use_container_width=True)
    else:
        st.sidebar.markdown("## 🌌 Nova Library")
        
    st.sidebar.markdown("### 🏛️ Elite Literacy Portal")
    
    with st.sidebar:
        st.divider()
        if not st.session_state.is_admin:
            with st.expander("🔐 Staff Access"):
                pwd = st.text_input("Admin PIN", type="password")
                if st.button("Unlock Dashboard", use_container_width=True):
                    if pwd == st.secrets.get("admin", {}).get("password", "NovaAdmin2026"):
                        st.session_state.is_admin = True
                        st.rerun()
                    else:
                        st.error("Invalid Credentials")
        else:
            st.success("👑 Staff Mode Active")
            if st.button("Lock Dashboard", use_container_width=True):
                st.session_state.is_admin = False
                st.rerun()

    if st.session_state.is_admin:
        tab_gallery, tab_member, tab_logistics, tab_admin = st.tabs([
            "🖼️ The Collection", "👤 Join Elite", "🚚 Delivery Hub", "⚙️ Admin & Acquisitions"
        ])
    else:
        tab_gallery, tab_member = st.tabs(["🖼️ The Collection", "👤 Join Elite"])
        tab_logistics = None
        tab_admin = None

    # --- 🖼️ TAB 1: ELITE GALLERY ---
    with tab_gallery:
        st.markdown("### 📚 The Nova Collection")
        
        # --- THE FLOATING MOBILE CART (F-String used safely here) ---
        if st.session_state.cart:
            total = len(st.session_state.cart) * 1500
            st.markdown(f"""
            <div class="floating-cart">
                <p style="margin:0; font-size:16px; font-weight:bold; color:var(--text-color);">🛒 {len(st.session_state.cart)} books selected (₦{total:,.2f})</p>
                <a href="?checkout=true" target="_self" class="checkout-btn">Proceed to Secure Checkout</a>
            </div>
            """, unsafe_allow_html=True)
        # -----------------------------

        response = supabase.table("lib_inventory").select("*").execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            col_search, col_filter = st.columns([3, 1])
            with col_search:
                search_query = st.text_input("🔍 Search Title or Author", placeholder="Type to search...")
            with col_filter:
                all_genres = ["All Categories"] + list(df['genre'].unique()) if 'genre' in df.columns else ["All Categories"]
                selected_genre = st.selectbox("Genre Filter", all_genres)
                
            filtered_df = df.copy()
            if search_query:
                filtered_df = filtered_df[
                    filtered_df['title'].str.contains(search_query, case=False) | 
                    filtered_df['author'].str.contains(search_query, case=False)
                ]
            if selected_genre != "All Categories":
                filtered_df = filtered_df[filtered_df['genre'] == selected_genre]
                
            if not filtered_df.empty:
                active_genres = filtered_df['genre'].unique()
                for genre in active_genres:
                    st.markdown(f"#### {genre}")
                    st.divider()
                    genre_books = filtered_df[filtered_df['genre'] == genre]
                    
                    cols = st.columns(4)
                    for idx, row in genre_books.reset_index().iterrows():
                        with cols[idx % 4]:
                            with st.container(border=True):
                                cover = row.get('cover_url') if row.get('cover_url') else "https://via.placeholder.com/200x300?text=No+Cover"
                                st.image(cover, use_container
