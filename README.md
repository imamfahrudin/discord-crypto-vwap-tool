# Discord Crypto VWAP Tool 🤖📊

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An intelligent Discord bot that scans cryptocurrency futures for VWAP (Volume Weighted Average Price) signals across multiple trading sessions. Features real-time scanning, technical indicators analysis, and interactive Discord bot commands with live-updating signal tables.

## 🌟 Features

- **Real-time VWAP Scanning**: Analyzes crypto futures using VWAP across Asian, London, and New York sessions
- **Multi-Interval Support**: Configure multiple refresh intervals for different time horizons (e.g., 10m, 30m, 1h)
- **Multi-Session Analysis**: Weighted scoring system for different trading sessions (Asian: 0.7x, London: 1.0x, New York: 1.2x)
- **Technical Indicators**: RSI, MACD, and Stochastic analysis for signal confirmation
- **Discord Bot Integration**: Interactive commands (`!start`, `!stop`) with live-updating signal tables
- **Independent Message Updates**: Multiple tables update independently at their own intervals
- **Volume Filtering**: Minimum volume thresholds to ensure signal quality
- **Configurable Scoring**: Customizable score thresholds for different signal strengths
- **Docker Support**: Ready-to-deploy with Docker and Docker Compose
- **Comprehensive Tables**: Professional signal tables with emojis and detailed metrics
- **Session-Based Weighting**: Different importance weights for each trading session
- **Error Handling**: Robust error handling and logging for reliable operation
- **Rate Limiting**: Built-in delays to respect API limits
- **Persistent State**: Bot remembers active scanners across restarts

## 📋 Prerequisites

- Python 3.9 or higher
- Docker and Docker Compose (optional, for containerized deployment)
- Discord Bot Token (create a bot at https://discord.com/developers/applications)
- Internet connection for API access

## 🤖 Discord Bot Setup

### Creating a Discord Bot

1. **Go to Discord Developer Portal**
   - Visit https://discord.com/developers/applications
   - Click "New Application" and give it a name

2. **Create a Bot**
   - Go to the "Bot" section in the left sidebar
   - Click "Add Bot" and confirm
   - Copy the **Token** (keep this secret!)

3. **Configure Bot Permissions**
   - Go to the "General Information" section
   - Copy the **Application ID**
   - Go to this URL to invite your bot: `https://discord.com/api/oauth2/authorize?client_id=YOUR_APPLICATION_ID&permissions=2048&scope=bot%20applications.commands`
   - Replace `YOUR_APPLICATION_ID` with your Application ID
   - Select your server and authorize the bot

4. **Required Permissions**
   - ✅ Send Messages
   - ✅ Use Slash Commands
   - ✅ Read Message History
   - ✅ Embed Links

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
DISCORD_BOT_TOKEN = "YOUR_DISCORD_BOT_TOKEN_HERE"

MAX_SYMBOLS = 120          # Maximum symbols to scan
# ⏱️ Refresh intervals in seconds (comma-separated for multiple tables)
# Examples: "120" (single 2m table), "600,1800,3600" (10m, 30m, 1h tables)
REFRESH_INTERVAL = "120"   # Can be single value or comma-separated
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
- **DISCORD_BOT_TOKEN** (required): Your Discord bot token from the Developer Portal
- **MAX_SYMBOLS** (optional): Maximum number of symbols to scan. Default: 120
- **REFRESH_INTERVAL** (optional): Refresh interval(s) in seconds. 
  - Single interval: `"120"` (one table updating every 2 minutes)
  - Multiple intervals: `"600,1800,3600"` (three tables: 10m, 30m, and 1h)
  - When multiple intervals are specified, each gets its own message that updates independently
  - Default: `"120"`
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
7. **Discord Bot Commands**: Use `/start` to begin scanning and `/stop` to end
8. **Live Updates**: Single message updates in real-time at configured intervals

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

## 🤖 Discord Bot Commands

### `!start`
- **Description**: Starts the VWAP scanner and sends live updates to the current channel
- **Usage**: Type `!start` in any text channel where the bot has permissions
- **Behavior**:
  - Sends initial message(s) with "Starting VWAP scanner..."
  - If single interval: Creates one message that updates at that interval
  - If multiple intervals: Creates separate messages for each interval (e.g., 10m, 30m, 1h)
  - Each message updates independently at its configured interval
  - Can run independently in multiple channels simultaneously
  - Only one scanner set per channel allowed

**Examples:**
- With `REFRESH_INTERVAL = "120"`: Creates 1 message updating every 2 minutes
- With `REFRESH_INTERVAL = "600,1800,3600"`: Creates 3 messages:
  - **10-minute table**: `BYBIT FUTURES VWAP SCANNER - 10M TIMEFRAME` (updates every 10 min)
  - **30-minute table**: `BYBIT FUTURES VWAP SCANNER - 30M TIMEFRAME` (updates every 30 min)
  - **1-hour table**: `BYBIT FUTURES VWAP SCANNER - 1H TIMEFRAME` (updates every hour)

Each table clearly displays its timeframe in both the Discord embed title and the table image header.

### `!stop`
- **Description**: Stops all VWAP scanner instances and ends live updates
- **Usage**: Type `!stop` while the scanner is running
- **Behavior**: 
  - Stops all interval timers for the current channel
  - Updates all messages with "VWAP scanner stopped"
  - Cleans up all running tasks and database entries

### Command Permissions
- Both commands are available to all users in channels where the bot has message permissions
- The bot must have "Send Messages" and "Embed Links" permissions in the channel

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
- **Issue**: Invalid Discord bot token
- **Solution**: Verify bot token in `config.py` and ensure the bot has proper permissions in your server

### Bot doesn't respond to commands
- **Issue**: Missing slash command permissions or bot not invited properly
- **Solution**: Ensure bot has "Use Slash Commands" permission and was invited with the correct scopes

### No signals generated
- **Issue**: API connection failure or low volume pairs
- **Solution**: Check internet connection and verify minimum volume settings

### Bot permissions errors
- **Issue**: Bot lacks required permissions in the channel
- **Solution**: Ensure bot has "Send Messages", "Use Slash Commands", and "Embed Links" permissions

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