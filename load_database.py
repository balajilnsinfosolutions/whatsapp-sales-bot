import requests
import pandas as pd
import os

from dotenv import load_dotenv

# LOAD ENV
load_dotenv()

# GOOGLE SHEET API URL
GOOGLE_SHEET_API = os.getenv("GOOGLE_SHEET_API")

# FETCH DATA
response = requests.get(GOOGLE_SHEET_API)

# CONVERT JSON
data = response.json()

# CREATE DATAFRAME
products_df = pd.DataFrame(data)

# PRINT DATA
print(products_df)