from shared.fyers_auth import generate_access_token
import json

auth_code = input("Enter auth_code: ").strip()

response = generate_access_token(auth_code)

print(json.dumps(response, indent=2))

with open("fyers_token.json", "w") as f:
    json.dump(response, f, indent=2)

print("Saved to fyers_token.json")