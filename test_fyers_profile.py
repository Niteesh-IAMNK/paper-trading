import os
from dotenv import load_dotenv
from fyers_apiv3 import fyersModel

load_dotenv()

fyers = fyersModel.FyersModel(
    client_id=os.getenv("FYERS_CLIENT_ID"),
    token=os.getenv("FYERS_ACCESS_TOKEN"),
    is_async=False
)

print(fyers.get_profile())