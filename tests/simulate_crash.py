import requests

payload = {
    "user_id": "user_001",
    "ticker": "AAPL",
    "price_change_percent": -15.4,
    "breaking_news_summary": (
        "Global semiconductor supply chain collapse "
        "causes panic across technology equities"
    )
}

r = requests.post(
    "http://127.0.0.1:8000/webhook/market-alert",
    json=payload
)

print(r.json())