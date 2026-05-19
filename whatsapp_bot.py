# =========================================
# IMPORT REQUIRED LIBRARIES
# =========================================

from difflib import get_close_matches
from load_database import products_df

import json
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
import os
import requests

# =========================================
# FLASK FOR WHATSAPP WEBHOOK
# =========================================

from flask import Flask, request


# =========================================
# LOAD ENVIRONMENT VARIABLES
# =========================================

load_dotenv()

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# =========================================
# GROQ CLIENT
# =========================================

client = Groq(api_key=GROQ_API_KEY)

# =========================================
# USER MEMORY
# =========================================

users = {}

# =========================================
# FLASK APP
# =========================================

app = Flask(__name__)
# =========================================
# DYNAMIC CATEGORY DETECTION
# =========================================

def detect_category(text):

    text = text.lower()

    for _, row in products_df.iterrows():

        category = str(row["product name"]).lower()

        keywords = str(row.get("Keywords", "")).lower()

        # =====================================
        # CHECK PRODUCT NAME
        # =====================================

        if category in text:
            return category

        # =====================================
        # CHECK KEYWORDS
        # =====================================

        keyword_list = keywords.split(",")

        for keyword in keyword_list:

            keyword = keyword.strip()

            if keyword and keyword in text:
                return category

    return None
# =========================================
# EXTRACT BUDGET
# =========================================

def extract_budget(text):

    budget = None

    words = text.lower().split()

    for word in words:

        clean_word = (
            word.replace("k", "")
            .replace(",", "")
            .replace("rs", "")
            .replace("₹", "")
            .strip()
        )

        # =====================================
        # CHECK NUMBER
        # =====================================

        if clean_word.isdigit():

            if "k" in word:
                budget = int(clean_word) * 1000
            else:
                budget = int(clean_word)

    return budget
# =========================================
# CREATE PRODUCT KNOWLEDGE
# =========================================

def generate_product_data():

    text = ""

    categories = products_df["product name"].unique()

    for category in categories:

        text += f"\n{category.upper()}:\n"

        # =====================================
        # FILTER CATEGORY
        # =====================================

        category_df = products_df[
            products_df["product name"].str.lower() == category.lower()
        ]

        brands = category_df["Brand Name"].dropna().unique()

        # =====================================
        # LOOP BRANDS
        # =====================================

        for brand in brands:

            text += f"\nBrand: {brand}\n"

            brand_df = category_df[
                category_df["Brand Name"].str.lower() == brand.lower()
            ]

            # =====================================
            # SIZES
            # =====================================

            sizes = brand_df["Sizes"].dropna().unique()

            if len(sizes) > 0:

                text += "Sizes:\n"

                for size in sizes:

                    if str(size).strip() != "":

                        text += f"- {size} inch\n"

            # =====================================
            # MODELS
            # =====================================

            models = brand_df["Model Name"].dropna().unique()

            if len(models) > 0:

                text += "Models:\n"

                for model in models:

                    if str(model).strip() != "":

                        text += f"- {model}\n"

            # =====================================
            # BROCHURES
            # =====================================

            brochures = brand_df["Brochure"].dropna().unique()

            if len(brochures) > 0:

                text += "Brochure Links:\n"

                for brochure in brochures:

                    if str(brochure).strip() != "":

                        text += f"- {brochure}\n"

    return text
# =========================================
# AI FUNCTION
# =========================================

def ask_ai(user_data, user_message):

    # =====================================
    # LOAD USER CHAT HISTORY
    # =====================================

    history = user_data["history"]

    # =====================================
    # LOAD USER DETAILS
    # =====================================

    category = user_data.get("category")
    budget = user_data.get("budget")

    # =====================================
    # GENERATE PRODUCT KNOWLEDGE
    # =====================================

    product_knowledge = generate_product_data()

    # =====================================
    # SYSTEM PROMPT
    # =====================================

    system_prompt = f"""
You are Gauri, a professional AI sales executive from Balaji LNS IT Solutions.

Available Products Data:
{product_knowledge}

Your behavior:
-WELCOME_MESSAGE = (
    "Hello 👋\n"
    "Welcome to Balaji LNS IT Solutions.\n"
    "I am Gauri.\n\n"
    "How can I help you today? 😊")
- Talk naturally like real WhatsApp sales executive
- Use emojis naturally
- Keep replies short
- Keep replies under 50 words
- Never generate fake prices
- Never say you are AI
- Use bullet points properly
- Continue same conversation topic
- Ask customer name first
Current Customer Data:

Name: {user_data.get("name")}
City: {user_data.get("city")}
Category: {category}
Budget: {budget}
"""

    # =====================================
    # CREATE MESSAGE LIST
    # =====================================

    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    # =====================================
    # ADD CHAT HISTORY
    # =====================================

    messages.extend(history)

    # =====================================
    # ADD CURRENT USER MESSAGE
    # =====================================

    messages.append({
        "role": "user",
        "content": user_message
    })

    # =====================================
    # GROQ AI API CALL
    # =====================================

    chat_completion = client.chat.completions.create(
        messages=messages,
        model="llama-3.3-70b-versatile"
    )

    # =====================================
    # EXTRACT AI REPLY
    # =====================================

    reply = chat_completion.choices[0].message.content

    # =====================================
    # SAVE USER MESSAGE
    # =====================================

    history.append({
        "role": "user",
        "content": user_message
    })

    # =====================================
    # SAVE AI REPLY
    # =====================================

    history.append({
        "role": "assistant",
        "content": reply
    })

    # =====================================
    # RETURN FINAL REPLY
    # =====================================

    return reply
# =========================================
# DEFAULT WELCOME MESSAGE
# =========================================

WELCOME_MESSAGE = (
    "Hello 👋\n"
    "Welcome to Balaji LNS IT Solutions.\n"
    "I am Gauri.\n\n"
    "How can I help you today? 😊"
)
# =========================================
# SAVE CRM DATA
# =========================================

def save_to_google_sheet(user_data, sender_number, user_message):

    try:

        # =====================================
        # GOOGLE APPS SCRIPT URL
        # =====================================

        url = "https://script.google.com/macros/s/AKfycbwCxqnpB2-5OROrm0nuNljSJe2ZDUFaMchL6fvkTcT96YOl1DXG6oCsbmh7FKSZVYjuCg/exec"

        # =====================================
        # CURRENT DATE & TIME
        # =====================================

        current_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        # =====================================
        # CRM DATA
        # =====================================

        data = {

            "name": user_data.get("name", ""),

            "location": user_data.get("city", ""),

            "requirement": user_data.get("brand", ""),

            "size": user_data.get("size", ""),

            "model": user_data.get("model", ""),

            "budget": str(user_data.get("budget", "")),

            "comment": user_message,

            "catalog_shared": "Yes" if user_data.get("catalog_sent") else "No",

            # =====================================
            # WHATSAPP MOBILE NUMBER
            # =====================================

            "mobile": sender_number,

            "datetime": current_time
        }

        # =====================================
        # SEND DATA TO GOOGLE SHEET
        # =====================================

        requests.post(
            url,
            json=data
        )

        print("CRM Data Saved")

    except Exception as e:

        print("Google Sheet Error:", e)

# =========================================
# HANDLE WHATSAPP MESSAGE
# =========================================

def handle_whatsapp_message(sender_number, user_message):

    # =====================================
    # USER ID = WHATSAPP NUMBER
    # =====================================

    user_id = sender_number

    # =====================================
    # CREATE USER MEMORY
    # =====================================

    if user_id not in users:

        users[user_id] = {

            "history": [],

            "category": None,

            "budget": None,

            "name": None,

            "city": None,

             "last_bot_reply": False

        }

    # =====================================
    # LOAD USER DATA
    # =====================================

    user_data = users[user_id]
    # =====================================
    # RESET BOT LOCK
    # =====================================

    user_data["last_bot_reply"] = False

    # =====================================
    # GREETING WORDS
    # =====================================

    greetings = [

        "hi",
        "hello",
        "hey",
        "hii",
        "heyy",
        "hy",
        "yo",
        "sup",
        "hola",
        "helloo",
        "he'll",
        "hlw",
        "namaste"
    ]

    # =====================================
    # SAVE NAME
    # =====================================

    clean_message = user_message.lower().strip()

    if (

        not user_data.get("name")

        and clean_message not in greetings

        and len(clean_message.split()) <= 3

        and clean_message.isalpha()

    ):

        user_data["name"] = user_message.title()

    # =====================================
    # SAVE CITY
    # =====================================

    elif (

        user_data.get("name")

        and not user_data.get("city")

        and clean_message not in greetings

    ):

        user_data["city"] = user_message

    # =====================================
    # DETECT CATEGORY
    # =====================================

    category = detect_category(user_message)

    if category:

        user_data["category"] = category
    # =========================================
    # DETECT BRAND & MODEL
    # =========================================

    all_brands = (
        products_df["Brand Name"]
        .dropna()
        .str.lower()
        .unique()
        .tolist()
    )

    for _, row in products_df.iterrows():

        model_name = str(row["Model Name"]).lower()

        # =====================================
        # DETECT MODEL
        # =====================================

        if model_name in user_message.lower():

            user_data["model"] = row["Model Name"]

    # =========================================
    # FUZZY BRAND MATCH
    # =========================================

    words = user_message.lower().split()

    for word in words:

        matched_brand = get_close_matches(

            word,

            all_brands,

            n=1,

            cutoff=0.6
        )

        if matched_brand:

            user_data["brand"] = matched_brand[0]

            break

    # =========================================
    # DETECT SIZE
    # =========================================

    import re

    size_match = re.search(

        r'\b(55|65|75|86|98)\b',

        user_message
    )

    if size_match:

        user_data["size"] = size_match.group(1)

    # =========================================
    # SEND PRODUCT BROCHURE
    # =========================================

    send_product_brochure(
        sender_number,
        user_message,
        user_data
    )

    # =====================================
    # EXTRACT BUDGET
    # =====================================

    budget = extract_budget(user_message)

    if budget:

        user_data["budget"] = budget

    # =====================================
    # GET AI REPLY
    # =====================================

    reply = ask_ai(user_data, user_message)

    # =====================================
    # SEND WHATSAPP MESSAGE
    # =====================================

    # =====================================
# SEND ONLY ONE MESSAGE
# =====================================

    if not user_data.get("last_bot_reply"):

        send_whatsapp_message(
            sender_number,
            reply
        )

        user_data["last_bot_reply"] = True
    # =====================================
    # SAVE CRM DATA
    # =====================================

    save_to_google_sheet(
        user_data,
        sender_number,
        user_message
    )
# =========================================
# AUTO BROCHURE SEND
# =========================================

def send_product_brochure(sender_number, user_message, user_data):

    for _, row in products_df.iterrows():

        # =====================================
        # LOAD PRODUCT DATA
        # =====================================

        brand_name = str(row["Brand Name"]).lower()

        size_value = str(row["Sizes"]).strip()

        brochure = str(row["Brochure"]).strip()

        # =====================================
        # MATCH BRAND OR SIZE
        # =====================================

        if (

            brand_name in user_message.lower()

            or size_value == user_message.lower()

        ):

            # =====================================
            # CHECK BROCHURE AVAILABLE
            # =====================================

            if brochure != "" and brochure.lower() != "nan":

                try:

                    # =====================================
                    # EXTRACT GOOGLE DRIVE FILE ID
                    # =====================================

                    file_id = brochure.split("/d/")[1].split("/")[0]

                    # =====================================
                    # GOOGLE DRIVE DOWNLOAD URL
                    # =====================================

                    download_url = (
                        f"https://drive.google.com/uc?export=download&id={file_id}"
                    )

                    # =====================================
                    # DOWNLOAD PDF
                    # =====================================

                    pdf_response = requests.get(download_url)

                    # =====================================
                    # CREATE FILE NAME
                    # =====================================

                    brand_name_clean = (
                        str(row["Brand Name"]).replace(" ", "_")
                    )

                    size_value_clean = (
                        str(row["Sizes"]).replace(" ", "_")
                    )

                    model_name = (
                        str(row["Model Name"]).replace(" ", "_")
                    )

                    # =====================================
                    # SAVE MODEL
                    # =====================================

                    user_data["model"] = model_name

                    # =====================================
                    # REMOVE NAN VALUES
                    # =====================================

                    if model_name.lower() == "nan":
                        model_name = ""

                    if size_value_clean.lower() == "nan":
                        size_value_clean = ""

                    # =====================================
                    # DYNAMIC PDF FILE NAME
                    # =====================================

                    pdf_filename = (
                        f"{brand_name_clean}_{size_value_clean}_{model_name}.pdf"
                    )

                    pdf_filename = pdf_filename.replace("__", "_")

                    # =====================================
                    # SAVE PDF FILE
                    # =====================================

                    with open(pdf_filename, "wb") as f:

                        f.write(pdf_response.content)

                    # =====================================
                    # SEND PDF TO WHATSAPP
                    # =====================================

                    # =====================================
# SEND ONLY IF BOT NOT REPLIED
# =====================================

                    if not user_data.get("last_bot_reply"):

                        send_whatsapp_document(
                            sender_number,
                            pdf_filename,
                            "📄 Product Catalogue"
                        )

                        user_data["last_bot_reply"] = True

                    # =====================================
                    # SAVE CATALOG STATUS
                    # =====================================

                    user_data["catalog_sent"] = True

                    print("Brochure Sent Successfully")

                    break

                except Exception as e:

                    print("Brochure Error:", e)
# =========================================
# SEND WHATSAPP MESSAGE
# =========================================

def send_whatsapp_message(to, message):

    url = (
        f"https://graph.facebook.com/v22.0/"
        f"{PHONE_NUMBER_ID}/messages"
    )

    headers = {

        "Authorization": f"Bearer {WHATSAPP_TOKEN}",

        "Content-Type": "application/json"
    }

    payload = {

        "messaging_product": "whatsapp",

        "to": to,

        "type": "text",

        "text": {
            "body": message
        }
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload
    )

    print(response.text)

# =========================================
# SEND WHATSAPP DOCUMENT
# =========================================

def send_whatsapp_document(to, file_path, caption):

    # =====================================
    # STEP 1 - UPLOAD FILE TO META
    # =====================================

    upload_url = (
        f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/media"
    )

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}"
    }

    files = {
        "file": open(file_path, "rb")
    }

    data = {
        "messaging_product": "whatsapp"
    }

    upload_response = requests.post(
        upload_url,
        headers=headers,
        files=files,
        data=data
    )

    media_id = upload_response.json()["id"]

    # =====================================
    # STEP 2 - SEND DOCUMENT
    # =====================================

    message_url = (
        f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    )

    payload = {

        "messaging_product": "whatsapp",

        "to": to,

        "type": "document",

        "document": {

            "id": media_id,

            "caption": caption,

            "filename": file_path
        }
    }

    requests.post(
        message_url,
        headers={
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        },
        json=payload
    )

# =========================================
# WHATSAPP WEBHOOK VERIFY
# =========================================

@app.route("/webhook", methods=["GET"])

def verify_webhook():

    verify_token = request.args.get("hub.verify_token")

    challenge = request.args.get("hub.challenge")

    if verify_token == VERIFY_TOKEN:

        return challenge

    return "Verification failed"


# =========================================
# RECEIVE WHATSAPP MESSAGE
# =========================================

@app.route("/webhook", methods=["POST"])

def webhook():

    data = request.get_json()

    try:

        # =====================================
        # EXTRACT MESSAGE DATA
        # =====================================

        entry = data["entry"][0]

        changes = entry["changes"][0]

        value = changes["value"]

        # =====================================
        # CHECK MESSAGE EXISTS
        # =====================================

        if "messages" in value:

            message = value["messages"][0]

            # =====================================
            # USER MESSAGE
            # =====================================

            user_message = (
                message["text"]["body"]
            )

            # =====================================
            # USER WHATSAPP NUMBER
            # =====================================

            sender_number = (
                message["from"]
            )

            print("Message:", user_message)

            # =====================================
            # HANDLE WHATSAPP MESSAGE
            # =====================================

            handle_whatsapp_message(

                sender_number,

                user_message
            )

    except Exception as e:

        print("Webhook Error:", e)

    return "ok", 200


# =========================================
# MAIN FUNCTION
# =========================================

def main():

    print("🤖 AI WhatsApp Sales Bot Running...")

    app.run(

        host="0.0.0.0",

        port=5000,

        debug=True
    )


# =========================================
# RUN WHATSAPP BOT
# =========================================

if __name__ == "__main__":

    main()