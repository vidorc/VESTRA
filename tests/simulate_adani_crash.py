import requests

payload = {
    "ticker": "ADANIENT",
    "price_change_percent": -15,
    "breaking_news_summary": "Corporate governance concerns trigger Adani crash"
}

r = requests.post(
    "http://127.0.0.1:8000/webhook/market-alert",
    json=payload
)

print(r.json())
