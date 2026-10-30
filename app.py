import streamlit as st
import pandas as pd
from pathlib import Path
import re

st.set_page_config(page_title="SmartBite Chatbot", page_icon="🍽️", layout="wide")

DATA_PATH = Path(__file__).parent / "restaurant_menu(3).csv"
IMAGES_DIR = Path(__file__).parent / "images"

@st.cache_data
def load_menu():
    df = pd.read_csv(DATA_PATH)
    df.columns = [str(c).strip() for c in df.columns]
    required = ["Dish_Name", "Cuisine", "Price", "Rating", "Veg_NonVeg"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("Dataset is missing required columns: " + ", ".join(missing))
    df["Dish_Name"] = df["Dish_Name"].fillna("Unknown dish").astype(str).str.strip()
    df["Cuisine"] = df["Cuisine"].fillna("Other").astype(str).str.strip()
    df["Veg_NonVeg"] = df["Veg_NonVeg"].fillna("Unknown").astype(str).str.strip()
    df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
    df["Rating"] = pd.to_numeric(df["Rating"], errors="coerce")
    return df.dropna(subset=["Price"]).copy()

try:
    menu = load_menu()
except Exception as e:
    st.error(f"Could not load the menu dataset: {e}")
    st.info("Make sure restaurant_menu(3).csv is in the same folder as app.py.")
    st.stop()

def image_for_dish(name):
    if not IMAGES_DIR.exists():
        return None
    key = re.sub(r"[^a-z0-9]+", "_", str(name).lower()).strip("_")
    candidates = [key + ".jpg", key + ".jpeg", key + ".png", key + ".webp"]
    for candidate in candidates:
        path = IMAGES_DIR / candidate
        if path.exists():
            return str(path)
    return None

def show_dish(row):
    cols = st.columns([1, 3])
    img = image_for_dish(row["Dish_Name"])
    with cols[0]:
        if img:
            st.image(img, use_container_width=True)
        else:
            st.markdown("🍽️")
    with cols[1]:
        st.markdown(f"**{row['Dish_Name']}**")
        st.write(f"{row['Cuisine']} · {row['Veg_NonVeg']} · ₹{row['Price']:.0f} · ⭐ {row['Rating'] if pd.notna(row['Rating']) else 'N/A'}")

def find_matches(query, veg=None, cuisine=None, max_price=None, min_rating=None):
    result = menu.copy()
    if query.strip():
        q = query.lower().strip()
        result = result[result.apply(lambda r: q in str(r["Dish_Name"]).lower()
                                     or q in str(r["Cuisine"]).lower()
                                     or q in str(r["Veg_NonVeg"]).lower(), axis=1)]
    if veg:
        result = result[result["Veg_NonVeg"].str.lower() == veg.lower()]
    if cuisine and cuisine != "All":
        result = result[result["Cuisine"].str.lower() == cuisine.lower()]
    if max_price is not None:
        result = result[result["Price"] <= max_price]
    if min_rating is not None:
        result = result[result["Rating"].fillna(0) >= min_rating]
    return result.sort_values(["Rating", "Price"], ascending=[False, True], na_position="last")

st.title("🍽️ SmartBite — Restaurant Chatbot")
st.caption("Explore the menu, get recommendations, and build a sample order.")

with st.sidebar:
    st.header("Find your food")
    search_text = st.text_input("Dish or cuisine", placeholder="e.g. burger, Indian")
    veg_filter = st.selectbox("Food preference", ["Any", "Veg", "Non-Veg"])
    cuisines = ["All"] + sorted(menu["Cuisine"].dropna().astype(str).unique().tolist())
    cuisine_filter = st.selectbox("Cuisine", cuisines)
    max_price = st.slider("Maximum price (₹)", 0, max(500, int(menu["Price"].max())), min(500, int(menu["Price"].max())))
    min_rating = st.slider("Minimum rating", 0.0, 5.0, 0.0, 0.5)
    recommend = st.button("Find dishes", type="primary", use_container_width=True)

tab_chat, tab_menu, tab_order = st.tabs(["💬 Chatbot", "📋 Full Menu", "🛒 Your Order"])

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi! I'm SmartBite. Ask me for vegetarian dishes, food under ₹200, a cuisine, or a dish name."}
    ]
if "cart" not in st.session_state:
    st.session_state.cart = {}

with tab_chat:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    prompt = st.chat_input("Ask SmartBite about the menu...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        q = prompt.lower()
        veg = "Veg" if any(x in q for x in ["vegetarian", "veg only", "veg dish", "veg dishes", "vegetarian", "veg"]) else None
        if "non-veg" in q or "non veg" in q or "nonvegetarian" in q:
            veg = "Non-Veg"
        budget = re.search(r"(?:under|below|less than|within|budget(?: of)?)\s*₹?\s*(\d+)", q)
        price_limit = float(budget.group(1)) if budget else None
        rating_match = re.search(r"(?:rating|rated)\s*(?:above|over|at least)?\s*(\d(?:\.\d)?)", q)
        rating_limit = float(rating_match.group(1)) if rating_match else None
        cuisine = next((c for c in menu["Cuisine"].dropna().astype(str).unique()
                        if c.lower() in q), None)
        dish_query = q
        for phrase in ["show me", "recommend", "suggest", "find", "search", "please", "i want", "give me", "dishes", "dish", "food", "menu", "under", "below", "less than", "within", "vegetarian", "veg only", "veg dish", "non-veg", "non veg", "budget"]:
            dish_query = dish_query.replace(phrase, " ")
        dish_query = re.sub(r"₹?\s*\d+", " ", dish_query).strip(" ?.,")
        if any(x in q for x in ["hello", "hi", "hey"]):
            answer = "Hello! Try asking “veg dishes under ₹200”, “Indian food”, or “show burger”."
            matches = pd.DataFrame()
        elif any(x in q for x in ["how many", "total dishes", "menu size"]):
            answer = f"Our menu currently has {len(menu)} rows and {menu['Dish_Name'].nunique()} unique dish names."
            matches = pd.DataFrame()
        else:
            matches = find_matches(dish_query, veg=veg, cuisine=cuisine, max_price=price_limit, min_rating=rating_limit)
            # If generic words leave a query that finds nothing, retry with filters only.
            if matches.empty and (veg or cuisine or price_limit is not None or rating_limit is not None):
                matches = find_matches("", veg=veg, cuisine=cuisine, max_price=price_limit, min_rating=rating_limit)
            if matches.empty:
                answer = "I couldn't find a matching dish. Try a dish name, cuisine, or a different budget."
            else:
                answer = f"I found {len(matches)} matching menu item(s). Here are the top options:"
        st.session_state.messages.append({"role": "assistant", "content": answer})
        st.rerun()
    # Show current results for the latest assistant response based on the most recent user message.
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant" and len(st.session_state.messages) >= 2:
        last_user = next((m["content"] for m in reversed(st.session_state.messages[:-1]) if m["role"] == "user"), None)
        if last_user:
            q = last_user.lower()
            veg = "Veg" if any(x in q for x in ["vegetarian", "veg only", "veg dish", "veg dishes", "veg"]) else None
            if "non-veg" in q or "non veg" in q:
                veg = "Non-Veg"
            budget = re.search(r"(?:under|below|less than|within|budget(?: of)?)\s*₹?\s*(\d+)", q)
            price_limit = float(budget.group(1)) if budget else None
            cuisine = next((c for c in menu["Cuisine"].dropna().astype(str).unique() if c.lower() in q), None)
            dish_query = q
            for phrase in ["show me", "recommend", "suggest", "find", "search", "please", "i want", "give me", "dishes", "dish", "food", "menu", "under", "below", "less than", "within", "vegetarian", "veg only", "veg dish", "non-veg", "non veg", "budget"]:
                dish_query = dish_query.replace(phrase, " ")
            dish_query = re.sub(r"₹?\s*\d+", " ", dish_query).strip(" ?.,")
            results = find_matches(dish_query, veg=veg, cuisine=cuisine, max_price=price_limit)
            if results.empty and (veg or cuisine or price_limit is not None):
                results = find_matches("", veg=veg, cuisine=cuisine, max_price=price_limit)
            if not results.empty and not any(x in q for x in ["hello", "hi", "hey", "how many", "total dishes", "menu size"]):
                for _, row in results.head(5).iterrows():
                    show_dish(row)
                    if st.button(f"Add {row['Dish_Name']} — ₹{row['Price']:.0f}", key=f"chatadd_{row['Dish_ID']}"):
                        item = str(row["Dish_ID"])
                        st.session_state.cart[item] = st.session_state.cart.get(item, 0) + 1
                        st.success(f"Added {row['Dish_Name']} to your order.")

with tab_menu:
    filtered = find_matches(search_text, veg=None if veg_filter == "Any" else veg_filter,
                            cuisine=cuisine_filter, max_price=max_price, min_rating=min_rating)
    st.write(f"Showing **{len(filtered)}** menu item(s).")
    if not filtered.empty:
        st.dataframe(filtered[["Dish_ID", "Dish_Name", "Cuisine", "Price", "Rating", "Veg_NonVeg"]],
                     use_container_width=True, hide_index=True)
        chosen = st.selectbox("Choose a dish to add to your order", filtered["Dish_Name"].drop_duplicates().tolist())
        selected_row = filtered[filtered["Dish_Name"] == chosen].iloc[0]
        if st.button("Add selected dish to order", key="menu_add"):
            item = str(selected_row["Dish_ID"])
            st.session_state.cart[item] = st.session_state.cart.get(item, 0) + 1
            st.success(f"Added {chosen} to your order.")
    else:
        st.info("No dishes match those filters. Try increasing the price limit or lowering the rating.")

with tab_order:
    if not st.session_state.cart:
        st.info("Your order is empty. Add dishes from the Chatbot or Full Menu tab.")
    else:
        total = 0.0
        for dish_id, qty in list(st.session_state.cart.items()):
            rows = menu[menu["Dish_ID"].astype(str) == dish_id]
            if rows.empty:
                continue
            row = rows.iloc[0]
            c1, c2, c3, c4 = st.columns([3, 1, 2, 1])
            c1.write(row["Dish_Name"])
            c2.write(f"× {qty}")
            c3.write(f"₹{row['Price'] * qty:.0f}")
            if c4.button("Remove", key=f"remove_{dish_id}"):
                del st.session_state.cart[dish_id]
                st.rerun()
            total += float(row["Price"]) * qty
        st.divider()
        st.subheader(f"Estimated total: ₹{total:.2f}")
        st.caption("Demo order only — this app does not process payments or send orders to a restaurant.")
        if st.button("Clear order"):
            st.session_state.cart = {}
            st.rerun()

if recommend:
    st.toast("Use the Full Menu tab to see the dishes matching your selected filters.")
