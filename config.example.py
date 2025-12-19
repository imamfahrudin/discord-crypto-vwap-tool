# config.example.py - Copy this to config.py and fill in your actual values

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN"

MAX_SYMBOLS = 120
REFRESH_INTERVAL = 120  # ⏱️

TOP_N = 15

# Minimum volume agar dianggap valid (dalam Million USDT)
MIN_VOLUME_M = 0.3

# Score threshold
STRONG_SCORE = 80
BUY_SCORE = 25
SELL_SCORE = -25
STRONG_SELL_SCORE = -80

SESSION_WEIGHTS = {
    "ASIAN": 0.7,
    "LONDON": 1.0,
    "NEW_YORK": 1.2
}