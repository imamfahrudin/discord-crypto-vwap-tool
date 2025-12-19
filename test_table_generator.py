#!/usr/bin/env python3
"""
Test script for table_generator.py
"""

import sys
import os
import logging
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from table_generator import generate_table_image
from datetime import datetime

# Set up custom logging with file details
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create console handler
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)

# Create formatter with file details in brackets
formatter = logging.Formatter('[%(filename)s:%(lineno)d] %(levelname)s: %(message)s')
handler.setFormatter(formatter)

# Add handler to logger
logger.addHandler(handler)

def test_rank_changes():
    """Test rank change functionality with simulated data changes"""

    # First run with initial rankings
    initial_data = """
================================================================================
BYBIT FUTURES VWAP SCANNER
================================================================================
Session: LONDON | Weight: 1.0
================================================================================
RANK SYMBOL         SIGNAL          SCORE   PRICE   VWAP    VOLUME  RSI     MACD    STOCH
================================================================================
1    BTCUSDT        STRONG BUY      95.2    45000   44500   1250000 65.4    0.002   78.5
2    ETHUSDT        BUY             87.8    2800    2750    890000  58.2    0.001   72.1
3    ADAUSDT        STRONG SELL     12.4    0.45    0.48    450000  32.1    -0.001  25.8
4    SOLUSDT        SELL            23.6    95.2    98.5    320000  41.7    -0.002  31.2
5    DOTUSDT        BUY             76.9    8.45    8.20    180000  55.8    0.0005  68.9
================================================================================
"""

    logger.info("Testing rank changes - First run (LONDON session)...")

    # Generate first table
    image_buffer1 = generate_table_image(
        table_data=initial_data,
        session_name="LONDON_TEST",
        weight="1.0",
        last_updated=datetime.now().strftime("%H:%M:%S"),
        footer_text="Test - First Run"
    )

    with open("test_rank_change_1.png", 'wb') as f:
        f.write(image_buffer1.getvalue())

    # Second run with changed rankings (simulate BTC dropping, ETH moving up)
    changed_data = """
================================================================================
BYBIT FUTURES VWAP SCANNER
================================================================================
Session: LONDON | Weight: 1.0
================================================================================
RANK SYMBOL         SIGNAL          SCORE   PRICE   VWAP    VOLUME  RSI     MACD    STOCH
================================================================================
1    ETHUSDT        STRONG BUY      92.1    2850    2800    950000  62.8    0.0015  75.2
2    BTCUSDT        BUY             88.5    45200   44800   1180000 63.1    0.0018  76.8
3    SOLUSDT        BUY             78.3    97.8    96.2    380000  57.4    0.0008  71.5
4    DOTUSDT        SELL            25.7    8.52    8.45    195000  48.2    -0.0002 45.3
5    ADAUSDT        STRONG SELL     15.8    0.46    0.49    420000  35.6    -0.0012 28.9
================================================================================
"""

    logger.info("Testing rank changes - Second run (LONDON session)...")

    # Generate second table with rank changes
    image_buffer2 = generate_table_image(
        table_data=changed_data,
        session_name="LONDON_TEST",
        weight="1.0",
        last_updated=datetime.now().strftime("%H:%M:%S"),
        footer_text="Test - Second Run with Changes"
    )

    with open("test_rank_change_2.png", 'wb') as f:
        f.write(image_buffer2.getvalue())

    logger.info("✅ Rank change test completed!")
    logger.info("📁 Check test_rank_change_1.png and test_rank_change_2.png")
    logger.info("   BTC should show ▼1 (moved down), ETH should show ▲1 (moved up)")

if __name__ == "__main__":
    test_rank_changes()