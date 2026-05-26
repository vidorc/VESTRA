import requests

payload = {
    "ticker": "RELIANCE",
    "price_change_percent": -25,
    "breaking_news_summary": "Extreme market collapse creates panic conditions"
}

r = requests.post(
    "http://127.0.0.1:8000/webhook/market-alert",
    json=payload
)

print(r.json())
