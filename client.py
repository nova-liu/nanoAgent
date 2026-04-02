import os
from openai import OpenAI
from config import API_KEY, BASE_URL

# Read the API key from the environment. Setup guide:
# https://www.volcengine.com/docs/82379/1399008

client = OpenAI(
    base_url=BASE_URL,
    api_key=API_KEY,
)
