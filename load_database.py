import requests
import pandas as pd
import os

from dotenv import load_dotenv

# LOAD ENV
load_dotenv()

# GOOGLE SHEET API URL
GOOGLE_SHEET_API = os.getenv("GOOGLE_SHEET_API")

try:

    # FETCH DATA
    response = requests.get(GOOGLE_SHEET_API)

    print("STATUS CODE:", response.status_code)
    print("RAW RESPONSE:", response.text)

    # CONVERT JSON
    data = response.json()

    # CREATE DATAFRAME
    products_df = pd.DataFrame(data)

    print(products_df)

except Exception as e:

    print("DATABASE LOAD ERROR:", e)

    # EMPTY DATAFRAME
    products_df = pd.DataFrame()