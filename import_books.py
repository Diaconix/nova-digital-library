import os
import qrcode
from supabase import create_client
import streamlit as st # Using this just to easily grab your secrets

# --- 1. CLOUD CONNECTION ---
# We pull the same secrets your app uses
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. THE STRUCTURED INVENTORY ---
# I have categorized your raw list and added the correct authors/genres
book_list = [
    # RAINBOW MAGIC SERIES
    {"title": "Layla the candyfloss fairy", "author": "Daisy Meadows", "genre": "Children's Fantasy"},
    {"title": "Jade the disco fairy", "author": "Daisy Meadows", "genre": "Children's Fantasy"},
    {"title": "Bethany the ballet fairy", "author": "Daisy Meadows", "genre": "Children's Fantasy"},
    {"title": "Jasmine the present fairy", "author": "Daisy Meadows", "genre": "Children's Fantasy"},
    {"title": "Saffron the yellow fairy", "author": "Daisy Meadows", "genre": "Children's Fantasy"},
    {"title": "Fern the green fairy", "author": "Daisy Meadows", "genre": "Children's Fantasy"},
    {"title": "Rebecca the rock 'n' roll fairy", "author": "Daisy Meadows", "genre": "Children's Fantasy"},
    {"title": "Polly the party fun fairy", "author": "Daisy Meadows", "genre": "Children's Fantasy"},
    {"title": "Saskia the salsa fairy", "author": "Daisy Meadows", "genre": "Children's Fantasy"},
    {"title": "Phoebe the fashion fairy", "author": "Daisy Meadows", "genre": "Children's Fantasy"},
    {"title": "Naomi the netball fairy", "author": "Daisy Meadows", "genre": "Children's Fantasy"},
    {"title": "Coco the cupcake fairy", "author": "Daisy Meadows", "genre": "Children's Fantasy"},
    {"title": "Izzy the indigo fairy", "author": "Daisy Meadows", "genre": "Children's Fantasy"},
    {"title": "Scarlett the garnet fairy", "author": "Daisy Meadows", "genre": "Children's Fantasy"},
    {"title": "Honey the sweet fairy", "author": "Daisy Meadows", "genre": "Children's Fantasy"},
    {"title": "Melody the music fairy", "author": "Daisy Meadows", "genre": "Children's Fantasy"},
    {"title": "Ruby the red fairy", "author": "Daisy Meadows", "genre": "Children's Fantasy"},
    {"title": "Kate the royal wedding fairy", "author": "Daisy Meadows", "genre": "Children's Fantasy"},
    {"title": "Amelia the singing fairy", "author": "Daisy Meadows", "genre": "Children's Fantasy"},
    {"title": "Lottie the lollipop fairy", "author": "Daisy Meadows", "genre": "Children's Fantasy"},
    {"title": "Amber the orange fairy", "author": "Daisy Meadows", "genre": "Children's Fantasy"},
    {"title": "Sky the blue fairy", "author": "Daisy Meadows", "genre": "Children's Fantasy"},
    {"title": "Evie the mist fairy", "author": "Daisy Meadows", "genre": "Children's Fantasy"},
    {"title": "Penny the pony fairy", "author": "Daisy Meadows", "genre": "Children's Fantasy"},

    # ADRIAN MOLE SERIES
    {"title": "The wilderness years", "author": "Sue Townsend", "genre": "Young Adult Fiction"},
    {"title": "The secret diary of Adrian Mole Aged 13 3/4", "author": "Sue Townsend", "genre": "Young Adult Fiction"},
    {"title": "True confessions of Adrian Albert Mole", "author": "Sue Townsend", "genre": "Young Adult Fiction"},
    {"title": "The crowning pain of Adrian Mole", "author": "Sue Townsend", "genre": "Young Adult Fiction"},
    {"title": "The cappuccino Years", "author": "Sue Townsend", "genre": "Young Adult Fiction"},

    # HORRIBLE SCIENCE & HISTORIES
    {"title": "Blood, Bones and Body Bits", "author": "Nick Arnold", "genre": "Science & History"},
    {"title": "Ugly Bugs", "author": "Nick Arnold", "genre": "Science & History"},
    {"title": "Chemical Chaos", "author": "Nick Arnold", "genre": "Science & History"},
    {"title": "Deadly Diseases", "author": "Nick Arnold", "genre": "Science & History"},
    {"title": "Disgusting Digestion", "author": "Nick Arnold", "genre": "Science & History"},
    {"title": "Bulging Brains", "author": "Nick Arnold", "genre": "Science & History"},
    {"title": "Evolve or Die", "author": "Nick Arnold", "genre": "Science & History"},
    {"title": "Terrible Tudors", "author": "Terry Deary", "genre": "Science & History"},
    {"title": "Awesome Egyptians", "author": "Terry Deary", "genre": "Science & History"},

    # ENID BLYTON - ST. CLARE'S
    {"title": "Kitty at St. Clare's", "author": "Pamela Cox / Enid Blyton", "genre": "Classic Children's Fiction"},
    {"title": "St. Clare's.. The First Year", "author": "Enid Blyton", "genre": "Classic Children's Fiction"},
    {"title": "Second Form at St. Clare's", "author": "Enid Blyton", "genre": "Classic Children's Fiction"},
    {"title": "The third form at St. Clare's", "author": "Enid Blyton", "genre": "Classic Children's Fiction"},
    {"title": "Claudine at St. Clare's", "author": "Enid Blyton", "genre": "Classic Children's Fiction"},
    {"title": "The twins at St. Clare's", "author": "Enid Blyton", "genre": "Classic Children's Fiction"}
]

# --- 3. CREATE QR OUTPUT FOLDER ---
output_dir = "physical_qr_codes"
os.makedirs(output_dir, exist_ok=True)

print(f"🚀 Initializing AICON Mass Import for {len(book_list)} books...")

# --- 4. EXECUTE UPLOAD & QR GENERATION ---
success_count = 0
for book in book_list:
    try:
        # Step A: Insert into Supabase
        # We set placeholder covers that your colleague can update later via the Admin tab
        book_data = {
            "title": book["title"],
            "author": book["author"],
            "genre": book["genre"],
            "condition": "Good",
            "status": "Available",
            "cover_url": "https://via.placeholder.com/300x450?text=Cover+Pending"
        }
        res = supabase.table("lib_inventory").insert(book_data).execute()
        
        if res.data:
            book_id = res.data[0]['id']
            
            # Step B: Generate the specific QR code for this UUID
            qr_url = f"https://aicon-library.streamlit.app/?id={book_id}"
            qr = qrcode.make(qr_url)
            
            # Clean title for filename (remove spaces and special chars)
            safe_title = "".join(x for x in book["title"] if x.isalnum() or x in " -_").replace(" ", "_")
            file_path = os.path.join(output_dir, f"{safe_title}.png")
            
            # Step C: Save locally
            qr.save(file_path)
            print(f"✅ Secured & Generated: {book['title']}")
            success_count += 1
            
    except Exception as e:
        print(f"⚠️ Error processing '{book['title']}': {str(e)}")

print(f"\n🏁 Import Complete. {success_count}/{len(book_list)} books processed.")
print(f"📂 You can find all QR codes ready for printing in the '{output_dir}' folder.")