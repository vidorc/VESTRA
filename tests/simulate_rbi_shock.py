import requests

payload = {
    "ticker": "HDFCBANK",
    "price_change_percent": -8,
    "breaking_news_summary": "RBI emergency repo rate hike shocks banking sector"
}

r = requests.post(
    "http://127.0.0.1:8000/webhook/market-alert",
    json=payload
)

print(r.json())
