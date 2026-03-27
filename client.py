import os
from openai import OpenAI

# Read the API key from the environment. Setup guide:
# https://www.volcengine.com/docs/82379/1399008
api_key = os.getenv('ARK_API_KEY')

client = OpenAI(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key=api_key,
)
    