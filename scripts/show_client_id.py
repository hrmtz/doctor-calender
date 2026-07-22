#!/usr/bin/env python3
import json, os
key = os.environ.get("GOOGLE_SERVICE_ACCOUNT_KEY", "secrets/service_account.json")
with open(key) as f:
    d = json.load(f)
print("client_id  :", d.get("client_id"))
print("client_email:", d.get("client_email"))
