# Discord Crypto VWAP Tool 🤖📊

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An intelligent Discord bot that scans cryptocurrency futures for VWAP (Volume Weighted Average Price) signals across multiple trading sessions. Features real-time scanning, technical indicators analysis, and automated Discord webhook notifications with comprehensive signal tables.

## 🌟 Features

- **Real-time VWAP Scanning**: Analyzes crypto futures using VWAP across Asian, London, and New York sessions
- **Multi-Session Analysis**: Weighted scoring system for different trading sessions (Asian: 0.7x, London: 1.0x, New York: 1.2x)
- **Technical Indicators**: RSI, MACD, and Stochastic analysis for signal confirmation
- **Discord Integration**: Automated webhook notifications with formatted signal tables
- **Volume Filtering**: Minimum volume thresholds to ensure signal quality
- **Configurable Scoring**: Customizable score thresholds for different signal strengths
- **Docker Support**: Ready-to-deploy with Docker and Docker Compose
- **Comprehensive Tables**: Professional signal tables with emojis and detailed metrics
- **Session-Based Weighting**: Different importance weights for each trading session
- **Error Handling**: Robust error handling and logging for reliable operation
- **Rate Limiting**: Built-in delays to respect API limits

## 📋 Prerequisites

- Python 3.9 or higher
- Docker and Docker Compose (optional, for containerized deployment)
- Discord webhook URL for notifications
- Internet connection for API access

## 🚀 Quick Start

### Option 1: Docker Deployment (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/imamfahrudin/discord-crypto-vwap-tool.git
   cd discord-crypto-vwap-tool
   ```

2. **Configure the bot**
   ```bash
   # Copy the example config file and edit with your Discord webhook URL
   cp config.example.py config.py
   nano config.py
   ```

3. **Build and run with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **View logs**
   ```bash
   docker-compose logs -f
   ```

### Option 2: Local Python Deployment

1. **Clone the repository**
   ```bash
   git clone https://github.com/imamfahrudin/discord-crypto-vwap-tool.git
   cd discord-crypto-vwap-tool
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the bot**
   ```bash
   # Copy and edit the config file
   cp config.example.py config.py
   # Edit config.py with your Discord webhook URL
   ```

5. **Run the bot**
   ```bash
   python main.py
   ```

## ⚙️ Configuration

### Config File Setup

Copy the example configuration file and customize it:

```bash
cp config.example.py config.py
```

Then edit `config.py` with your settings:

```python
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN"

MAX_SYMBOLS = 120          # Maximum symbols to scan
REFRESH_INTERVAL = 120     # Scan interval in seconds
TOP_N = 15                 # Number of top signals to display
MIN_VOLUME_M = 0.3         # Minimum volume in millions USDT

# Score thresholds for signals
STRONG_SCORE = 80
BUY_SCORE = 25
SELL_SCORE = -25
STRONG_SELL_SCORE = -80

# Session weights for different trading sessions
SESSION_WEIGHTS = {
    "ASIAN": 0.7,     # Asian session weight
    "LONDON": 1.0,    # London session weight
    "NEW_YORK": 1.2   # New York session weight
}
```

**Configuration Options:**
- **DISCORD_WEBHOOK_URL** (required): Your Discord webhook URL for sending notifications
- **MAX_SYMBOLS** (optional): Maximum number of symbols to scan. Default: 120
- **REFRESH_INTERVAL** (optional): How often to scan in seconds. Default: 120
- **TOP_N** (optional): Number of top signals to display. Default: 15
- **MIN_VOLUME_M** (optional): Minimum volume in millions USDT. Default: 0.3
- **Score Thresholds**: Customize signal strength thresholds
- **SESSION_WEIGHTS**: Weight different trading sessions (Asian/London/New York)

## 🔧 How It Works

1. **Initialization**: Bot loads configuration and establishes connections
2. **Data Collection**: Fetches real-time price and volume data from Bybit futures
3. **VWAP Calculation**: Computes Volume Weighted Average Price for each session
4. **Technical Analysis**: Applies RSI, MACD, and Stochastic indicators
5. **Signal Scoring**: Calculates weighted scores based on session importance
6. **Table Generation**: Creates formatted signal tables with emojis and metrics
7. **Discord Notification**: Sends automated webhook notifications with signal tables
8. **Continuous Scanning**: Repeats the process at configured intervals

## 📊 Usage

### Signal Table Format

The bot generates professional signal tables with the following columns:

```
BYBIT FUTURES VWAP SESSION SCANNER
Session : LONDON | Weight : 1.0
================================================================================
RANK  SYMBOL          SIGNAL               SCORE    PRICE       VWAP        VOL(M)   RSI    MACD     STOCH
================================================================================
1     BTCUSDT         🟢🔥 STRONG BUY       85.2    45123.45    44980.12    1250.3   72.1   245.6    78.4
2     ETHUSDT         🟢 BUY                42.8    2456.78     2430.15     890.7    68.9   123.4    65.2
...
```

### Signal Types

- **🟢🔥 STRONG BUY**: Score ≥ 80 (High confidence buy signal)
- **🟢 BUY**: Score ≥ 25 (Moderate buy signal)
- **⚪ NEUTRAL**: Score between -25 and 25 (No clear signal)
- **🔴 SELL**: Score ≤ -25 (Moderate sell signal)
- **🔴🔥 STRONG SELL**: Score ≤ -80 (High confidence sell signal)

### Session Analysis

The bot analyzes three major trading sessions with different weights:

- **ASIAN** (0.7x weight): Asian trading hours
- **LONDON** (1.0x weight): European trading hours
- **NEW_YORK** (1.2x weight): US trading hours

Higher weight sessions have more influence on the final signal score.

## 📝 Logging

The bot provides console logging for monitoring:

- **[INFO]**: General information and status updates
- **[ERROR]**: Critical errors that require attention
- **[SCAN]**: Scanning progress and signal generation details

View logs in real-time:
```bash
# Docker
docker-compose logs -f

# Local Python
# Logs appear in the console where you ran python main.py
```

## 🐛 Troubleshooting

### Bot doesn't start
- **Issue**: Invalid Discord webhook URL
- **Solution**: Verify webhook URL in `config.py` and ensure it has proper permissions

### No signals generated
- **Issue**: API connection failure or low volume pairs
- **Solution**: Check internet connection and verify minimum volume settings

### Webhook errors
- **Issue**: Discord webhook issues
- **Solution**: Verify webhook URL is correct and hasn't expired

### Configuration errors
- **Issue**: Missing or invalid config.py
- **Solution**: Ensure `config.py` exists and is properly formatted. Copy from `config.example.py`

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Bybit](https://www.bybit.com/) for exchange data and API access
- [pandas](https://pandas.pydata.org/) for data manipulation
- [requests](https://requests.readthedocs.io/) for HTTP client functionality

## 📧 Contact

**Repository**: [https://github.com/imamfahrudin/discord-crypto-vwap-tool](https://github.com/imamfahrudin/discord-crypto-vwap-tool)

**Issues**: [Report a bug or request a feature](https://github.com/imamfahrudin/discord-crypto-vwap-tool/issues)

---

Made with ❤️ for the crypto trading community