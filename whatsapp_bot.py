# =========================================
# IMPORT REQUIRED LIBRARIES
# =========================================
from load_database import products_df

from groq import Groq
from dotenv import load_dotenv
import os

from flask import Flask, request
import requests
# =========================================
# LOAD ENVIRONMENT VARIABLES
# =========================================

load_dotenv()
app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
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
# SEND WHATSAPP MESSAGE
# =========================================

def send_message(phone_number, message):

    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "text",
        "text": {
            "body": message
        }
    }

    response = requests.post(
        url,
        headers=headers,
        json=data
    )

    print(response.text)

# =========================================
# DYNAMIC CATEGORY DETECTION
# WHATSAPP BOT
# =========================================

def detect_category(user_message):

    text = user_message.lower()

    # LOOP THROUGH GOOGLE SHEET DATA
    for _, row in products_df.iterrows():

        # PRODUCT CATEGORY
        category = str(row["product name"]).lower().strip()

        # OPTIONAL KEYWORDS COLUMN
        keywords = str(row.get("Keywords", "")).lower()

        # CHECK PRODUCT NAME
        if category in text:
            return category

        # CHECK KEYWORDS
        keyword_list = keywords.split(",")

        for keyword in keyword_list:

            keyword = keyword.strip()

            if keyword and keyword in text:
                return category

    return None
# =========================================
# EXTRACT BUDGET
# WHATSAPP BOT
# =========================================

def extract_budget(user_message):

    text = user_message.lower()

    budget = None

    words = text.split()

    for word in words:

        # REMOVE SYMBOLS
        clean_word = (
            word.replace("k", "")
            .replace("rs", "")
            .replace("₹", "")
            .replace(",", "")
            .replace("rupees", "")
        )

        # CHECK NUMBER
        if clean_word.isdigit():

            # HANDLE 80k
            if "k" in word:
                budget = int(clean_word) * 1000

            # HANDLE NORMAL NUMBER
            else:
                budget = int(clean_word)

    return budget
# =========================================
# CREATE PRODUCT KNOWLEDGE
# WHATSAPP BOT
# =========================================

def generate_product_data():

    knowledge_text = ""

    # GET ALL PRODUCT CATEGORIES
    categories = products_df["product name"].dropna().unique()

    for category in categories:

        knowledge_text += f"\n📦 {str(category).upper()}\n"

        # FILTER CATEGORY
        category_df = products_df[
            products_df["product name"].str.lower() == str(category).lower()
        ]

        # GET BRANDS
        brands = category_df["Brand Name"].dropna().unique()

        for brand in brands:

            knowledge_text += f"\n🏷️ Brand: {brand}\n"

            # FILTER BRAND
            brand_df = category_df[
                category_df["Brand Name"].str.lower() == str(brand).lower()
            ]

            # =====================================
            # SIZES
            # =====================================

            sizes = brand_df["Sizes"].dropna().unique()

            valid_sizes = []

            for size in sizes:

                if str(size).strip() != "":
                    valid_sizes.append(size)

            if len(valid_sizes) > 0:

                knowledge_text += "📏 Sizes:\n"

                for size in valid_sizes:
                    knowledge_text += f"   • {size} inch\n"

            # =====================================
            # MODELS
            # =====================================

            models = brand_df["Model Name"].dropna().unique()

            valid_models = []

            for model in models:

                if str(model).strip() != "":
                    valid_models.append(model)

            if len(valid_models) > 0:

                knowledge_text += "🛠️ Models:\n"

                for model in valid_models:
                    knowledge_text += f"   • {model}\n"

            # =====================================
            # PRICE
            # =====================================

            prices = brand_df["Price"].dropna().unique()

            valid_prices = []

            for price in prices:

                if str(price).strip() != "":
                    valid_prices.append(price)

            if len(valid_prices) > 0:

                knowledge_text += "💰 Price Range:\n"

                for price in valid_prices:
                    knowledge_text += f"   • ₹{price}\n"

    return knowledge_text
# =========================================
# AI FUNCTION
# WHATSAPP BOT
# =========================================

def ask_ai(user_data, user_message):

    history = user_data.get("history", [])

    category = user_data.get("category", "")
    budget = user_data.get("budget", "")

    # PRODUCT KNOWLEDGE FROM GOOGLE SHEET
    product_knowledge = generate_product_data()

    # =====================================
    # SYSTEM PROMPT
    # =====================================

    system_prompt = f"""
You are Gauri, a professional WhatsApp sales executive from Balaji LNS IT Solutions.

AVAILABLE PRODUCT DATABASE:
{product_knowledge}

YOUR BEHAVIOR:

- Talk naturally like a real human sales executive
- Keep replies attractive and premium
- Use emojis naturally
- Use short messages
- Use bullet points properly
- Use line breaks properly
- Keep replies under 50 words
- Never generate long paragraphs
- Never say you are AI
- Continue same conversation naturally
- Never ask repeated questions
- Be professional and friendly

LANGUAGE RULES:
- Hindi → Hindi
- English → English
- Hinglish → Hinglish

CONVERSATION FLOW:

Name → City → Product → Brand → Size/Model → Budget/Price

IMPORTANT RULES:

1. If customer already shared:
- Name
- City
- Budget

DO NOT ask again.

2. Never switch category randomly.

3. Never show products from wrong category.

4. If customer asks unavailable products like:
- pc
- laptop
- cpu
- keyboard
- mobile

Reply:

Currently we deal in:

✅ Smart Boards
✅ PTZ Cameras
✅ Studio Lights
✅ Microphones

Please let us know your requirement 😊

5. If customer asks price:

DO NOT generate fake prices.

Reply:

"Our sales executive will connect with you shortly and share complete quotation details 😊"

6. Smart Board Flow:

Brand → Size → Model (if available) → Price/Budget

7. PTZ Camera Flow:

Brand → Mode → Price/Budget

8. Lights Flow:

Brand → Model → Price/Budget

9. Microphone Flow:

Brand → Model → Price/Budget

CURRENT CUSTOMER DATA:

Category: {category}
Budget: {budget}
"""

    # =====================================
    # MESSAGES
    # =====================================

    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    # CHAT HISTORY
    messages.extend(history)

    # CURRENT USER MESSAGE
    messages.append(
        {
            "role": "user",
            "content": user_message
        }
    )

    # =====================================
    # AI RESPONSE
    # =====================================

    chat_completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages
    )

    ai_reply = chat_completion.choices[0].message.content

    # SAVE HISTORY
    history.append({
        "role": "user",
        "content": user_message
    })

    history.append({
        "role": "assistant",
        "content": ai_reply
    })

    user_data["history"] = history

    return ai_reply
# =========================================
# GREETING MESSAGE
# WHATSAPP BOT
# =========================================

def get_welcome_message():

    return (
        "Hello 👋\n\n"
        "Welcome to *Balaji LNS IT Solutions* ✨\n"
        "I am *Gauri* 😊\n\n"
        "How can I help you today?"
    )
# =========================================
# WHATSAPP WEBHOOK
# HANDLE MESSAGE
# =========================================

@app.route("/webhook", methods=["GET", "POST"])
def webhook():

    # =====================================
    # META WEBHOOK VERIFICATION
    # =====================================

    if request.method == "GET":

        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200

        return "Verification failed", 403

    # =====================================
    # RECEIVE WHATSAPP MESSAGE
    # =====================================

    data = request.get_json()

    

    try:

        # =====================================
        # GET WHATSAPP MESSAGE
        # =====================================

        entry = data["entry"][0]

        changes = entry["changes"][0]

        value = changes["value"]

        messages = value.get("messages")

        if messages:

            message = messages[0]

            # USER PHONE NUMBER
            phone_number = message["from"]

            # USER MESSAGE
            user_message = message["text"]["body"]

            # =====================================
            # CREATE USER MEMORY
            # =====================================

            if phone_number not in users:

                users[phone_number] = {
                    "history": [],
                    "category": None,
                    "budget": None
                }

            user_data = users[phone_number]

            # =====================================
            # GREETING HANDLER
            # =====================================

            greetings = ["hi", "hello", "hey", "hii"]

            if user_message.lower() in greetings:

                reply = get_welcome_message()

                send_message(phone_number, reply)

                return "ok", 200

            # =====================================
            # DETECT CATEGORY
            # =====================================

            category = detect_category(user_message)

            if category:

                user_data["category"] = category

            # =====================================
            # DETECT BUDGET
            # =====================================

            budget = extract_budget(user_message)

            if budget:

                user_data["budget"] = budget

            # =====================================
            # SAVE USER MESSAGE
            # =====================================

            user_data["history"].append({
                "role": "user",
                "content": user_message
            })

            # KEEP LAST 10 CHATS
            user_data["history"] = user_data["history"][-10:]

            # =====================================
            # ASK AI
            # =====================================

            try:

                reply = ask_ai(user_data, user_message)

            except Exception as e:

                print(e)

                reply = (
                    "Sorry sir 😊\n"
                    "Currently server busy hai.\n"
                    "Please try again later."
                )

            # =====================================
            # SAVE AI REPLY
            # =====================================

            user_data["history"].append({
                "role": "assistant",
                "content": reply
            })

            # =====================================
            # SEND WHATSAPP MESSAGE
            # =====================================

            send_message(phone_number, reply)

    except Exception as e:

        print(e)

    return "ok", 200



# =========================================
# RUN WHATSAPP SERVER
# =========================================

if __name__ == "__main__":

    print("🤖 WhatsApp AI Sales Bot Running...")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )