# notifier/discord_webhook.py

import requests
import logging
from config import DISCORD_WEBHOOK_URL

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('[%(filename)s:%(lineno)d] %(levelname)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

MAX_DISCORD_CHARS = 1800  # buffer aman

def send_table(table_text: str):
    if not DISCORD_WEBHOOK_URL:
        logger.warning("Discord webhook URL kosong")
        return

    chunks = [
        table_text[i:i + MAX_DISCORD_CHARS]
        for i in range(0, len(table_text), MAX_DISCORD_CHARS)
    ]

    for idx, chunk in enumerate(chunks, 1):
        payload = {
            "content": f"```\n{chunk}\n```"
        }

        r = requests.post(
            DISCORD_WEBHOOK_URL,
            json=payload,
            timeout=10
        )

        if r.status_code not in (200, 204):
            logger.error(f"Discord error: {r.status_code} {r.text}")
        else:
            logger.info(f"Discord chunk {idx}/{len(chunks)} sent")
