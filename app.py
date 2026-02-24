import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client
import qrcode
from io import BytesIO
import os

# --- 1. CONFIG & BRANDING ---
st.set_page_config(page_title="Nova Digital Library", page_icon="assets/favicon.png", layout="wide")

st.markdown("""
    <style>
    .stApp {
        background-color: #f8f9fa;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    [data-testid="stHeader"] {
        background-color: #ffffff;
        border-bottom: 1px solid #dee2e6;
    }
    div.stButton > button {
        border-radius: 20px;
        background-color: #2c3e50; 
        color: white;
    }
    .aicon-watermark {
        position: fixed;
        bottom: 10px;
        right: 15px;
        font-size: 11px;
        color: #cbd5e1;
        font-family: monospace;
        z-index: 9999;
        user-select: none;
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

# Initialize Shopping Cart
if 'cart' not in st.session_state:
    st.session_state.cart = []

# Initialize Admin Authentication State
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
    # ROUTE A: EXPRESS CHECKOUT (MULTI-ITEM CAPABLE)
    # ---------------------------------------------------------
    st.markdown("## 📱 Nova Secure Checkout")
    
    try:
        res = supabase.table("lib_inventory").select("*").in_("id", checkout_ids).execute()
        
        if res.data:
            books = res.data
            total_price = sum(get_rental_price(b) for b in books)
            selar_link = "https://selar.com/d20is52cl1" 
            
            st.markdown("### 🛒 Your Selection:")
            for b in books:
                st.markdown(f"- **{b['title']}** *(by {b['author']})* - ₦{get_rental_price(b):,.2f}")
            
            st.markdown(f"### **Total Amount: ₦{total_price:,.2f}**")
            st.divider()
            
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
                    
                    if st.button("Verify & Generate Payment Link", type="primary"):
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
                    
                    if st.button("Reserve & Generate Payment Link", type="primary"):
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
            if st.button("← Back to Main Library"):
                st.query_params.clear()
                st.rerun()
        else:
            st.error("🚨 Book(s) not found.")
    except Exception as e:
        st.error(f"Database connection error: {e}")

else:
    # ---------------------------------------------------------
    # ROUTE B: THE DASHBOARD TABS (WITH RBAC SECURITY)
    # ---------------------------------------------------------
    
    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        st.sidebar.image(logo_path, use_container_width=True)
    else:
        st.sidebar.markdown("## 🌌 Nova Library")
        
    st.sidebar.markdown("### 🏛️ Elite Literacy Portal")
    
    # --- ADMIN LOGIN KEYHOLE ---
    with st.sidebar:
        st.divider()
        if not st.session_state.is_admin:
            with st.expander("🔐 Staff Access"):
                pwd = st.text_input("Admin PIN", type="password")
                if st.button("Unlock Dashboard", use_container_width=True):
                    # Check against the secret password we added
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

    # --- DYNAMIC TAB GENERATION ---
    if st.session_state.is_admin:
        # Admin sees everything
        tab_gallery, tab_member, tab_logistics, tab_admin = st.tabs([
            "🖼️ The Collection", "👤 Join Elite", "🚚 Delivery Hub", "⚙️ Admin & Acquisitions"
        ])
    else:
        # Public only sees the Gallery and Membership Signup
        tab_gallery, tab_member = st.tabs(["🖼️ The Collection", "👤 Join Elite"])
        tab_logistics = None
        tab_admin = None

    # --- 🖼️ TAB 1: ELITE GALLERY ---
    with tab_gallery:
        st.markdown("### 📚 The Nova Collection")
        
        if st.session_state.cart:
            st.success(f"🛒 **{len(st.session_state.cart)} books selected.** Total: ₦{len(st.session_state.cart)*1500:,.2f}")
            if st.button("Proceed to Checkout", type="primary", use_container_width=True):
                st.query_params["checkout"] = "true"
                st.rerun()
            st.divider()

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
                                st.image(cover, use_container_width=True)
                                st.markdown(f"**{row['title']}**")
                                st.caption(f"_{row['author']}_")
                                
                                status = row.get('status', 'Available')
                                if status == "Available":
                                    st.markdown(":green[● Available]")
                                    
                                    if row['id'] in st.session_state.cart:
                                        if st.button("Remove from Selection", key=f"rem_{row['id']}", use_container_width=True):
                                            st.session_state.cart.remove(row['id'])
                                            st.rerun()
                                    else:
                                        if st.button("Add to Selection", key=f"add_{row['id']}", use_container_width=True):
                                            st.session_state.cart.append(row['id'])
                                            st.rerun()
                                            
                                elif status == "Reserved":
                                    st.markdown(":orange[● Reserved (Pending Payment)]")
                                    st.button("Unavailable", key=f"btn_r_{row['id']}", disabled=True, use_container_width=True)
                                else:
                                    st.markdown(":red[● Rented Out]")
                                    st.button("Unavailable", key=f"btn_u_{row['id']}", disabled=True, use_container_width=True)
            else:
                st.info("No books found matching your search.")
        else:
            st.warning("📭 The Library is currently empty.")

    # --- 👤 TAB 2: MEMBER ONBOARDING ---
    with tab_member:
        st.header("👤 Join the Nova Elite Readers")
        with st.form("new_member_form"):
            c1, c2 = st.columns(2)
            with c1:
                f_name = st.text_input("Full Name")
                email = st.text_input("Email Address")
            with c2:
                phone = st.text_input("WhatsApp Number")
                tier = st.selectbox("Membership Tier", ["Silver (Pickup Only)", "Gold (Standard Delivery)", "Elite (Priority Access)"])
            addr = st.text_area("Delivery Address (Required for Gold/Elite)")
            if st.form_submit_button("Activate Membership"):
                if f_name and email:
                    new_member = {"full_name": f_name, "email": email.strip().lower(), "phone": phone, "delivery_address": addr, "membership_tier": tier}
                    try:
                        supabase.table("lib_members").insert(new_member).execute()
                        st.success(f"Welcome, {f_name}! Your {tier} membership is active.")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Registration Failed: {e}")
                else:
                    st.warning("Name and Email are required.")

    # --- 🚚 TAB 3: DELIVERY HUB & PAYMENTS (ADMIN ONLY) ---
    if tab_logistics:
        with tab_logistics:
            st.header("🚚 Logistics & Payment Hub")
            st.write("Reconcile Selar transactions and manage dispatch riders.")
            
            try:
                res = supabase.table("lib_rentals").select(
                    "id, book_id, due_date, delivery_type, delivery_status, is_paid, lib_inventory(title), lib_members(full_name, phone)"
                ).execute()
                
                if res.data:
                    formatted_data = []
                    for r in res.data:
                        book_title = r.get("lib_inventory", {}).get("title", "Unknown") if r.get("lib_inventory") else "Unknown"
                        
                        if r.get("lib_members"):
                            customer = r["lib_members"].get("full_name", "Unknown")
                            contact = r["lib_members"].get("phone", "N/A")
                        else:
                            customer = r.get("delivery_type", "Guest").replace("Pickup by ", "")
                            contact = "Guest (No Phone)"
                            
                        formatted_data.append({
                            "Ref ID": str(r["id"])[:8],
                            "Book": book_title,
                            "Customer": customer,
                            "Contact": contact,
                            "Method": "🚚 Delivery" if "Home Delivery" in r["delivery_type"] else "🚶 Pickup",
                            "Payment": "✅ Paid" if r["is_paid"] else "⏳ Pending Selar",
                            "Status": r["delivery_status"],
                            "_raw_id": r["id"],
                            "_book_id": r["book_id"]
                        })
                        
                    df_log = pd.DataFrame(formatted_data)
                    
                    st.dataframe(
                        df_log.drop(columns=["_raw_id", "_book_id"]), 
                        use_container_width=True, 
                        hide_index=True
                    )
                    
                    st.divider()
                    st.subheader("⚙️ Dispatch & Update Desk")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        options = df_log.apply(lambda x: f"{x['Ref ID']} - {x['Customer']} ({x['Book']})", axis=1).tolist()
                        selected_display = st.selectbox("Select Transaction to Update", options)
                        selected_index = options.index(selected_display)
                        
                        target_uuid = df_log.iloc[selected_index]["_raw_id"]
                        target_book_id = df_log.iloc[selected_index]["_book_id"]
                        
                    with c2:
                        new_status = st.selectbox(
                            "Action / Update Status", 
                            [
                                "Payment Confirmed - Awaiting Dispatch", 
                                "In-Transit (Rider Dispatched)", 
                                "Picked Up (Library Desk)", 
                                "Returned & Completed"
                            ]
                        )
                        
                    if st.button("Commit Update to Ledger", type="primary"):
                        update_payload = {"delivery_status": new_status}
                        if "Payment Confirmed" in new_status:
                            update_payload["is_paid"] = True
                            
                        supabase.table("lib_rentals").update(update_payload).eq("id", target_uuid).execute()
                        
                        if new_status in ["In-Transit (Rider Dispatched)", "Picked Up (Library Desk)"]:
                            supabase.table("lib_inventory").update({"status": "Rented"}).eq("id", target_book_id).execute()
                        elif new_status == "Returned & Completed":
                            supabase.table("lib_inventory").update({"status": "Available"}).eq("id", target_book_id).execute()
                            
                        st.success(f"Ledger & Inventory updated for {selected_display}!")
                        st.info("🔄 Refresh the page to see the updated table.")
                        
                else:
                    st.info("✅ The ledger is currently clear. No pending rentals or pickups.")
                    
            except Exception as e:
                st.error(f"Dashboard Integration Error: {e}")

    # --- ⚙️ TAB 4: ADMIN & ACQUISITIONS (ADMIN ONLY) ---
    if tab_admin:
        with tab_admin:
            st.header("📚 Catalog New Acquisition")
            with st.form("add_book_form"):
                col1, col2 = st.columns(2)
                with col1:
                    title = st.text_input("Book Title")
                    author = st.text_input("Author")
                with col2:
                    genre = st.selectbox("Genre", ["Fiction", "Non-Fiction", "Sci-Fi", "History", "Children's Fantasy", "Education"])
                    condition = st.select_slider("Condition", ["Fair", "Good", "Very Good", "New"])
                cover_url = st.text_input("Cover Image URL")
                if st.form_submit_button("Catalog Book"):
                    if title and author:
                        book_data = {"title": title, "author": author, "genre": genre, "condition": condition, "cover_url": cover_url, "status": "Available"}
                        res = supabase.table("lib_inventory").insert(book_data).execute()
                        if res.data:
                            st.success(f"'{title}' added to inventory!")
                            st.image(get_qr(res.data[0]['id']), width=150)