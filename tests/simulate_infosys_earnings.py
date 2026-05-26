import requests

payload = {
    "ticker": "INFY",
    "price_change_percent": -11,
    "breaking_news_summary": "Infosys misses quarterly earnings expectations"
}

r = requests.post(
    "http://127.0.0.1:8000/webhook/market-alert",
    json=payload
)

print(r.json())
