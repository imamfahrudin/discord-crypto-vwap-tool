# Discord Crypto VWAP Tool 🤖📊

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An intelligent Discord bot that scans cryptocurrency futures for VWAP (Volume Weighted Average Price) signals across multiple trading sessions. Features real-time scanning, technical indicators analysis, and interactive Discord bot commands with live-updating signal tables.

## 🌟 Features

- **Real-time VWAP Scanning**: Analyzes crypto futures using VWAP across Sydney, Tokyo, London, and New York sessions
- **Multi-Interval Support**: Configure multiple refresh intervals for different time horizons (e.g., 10m, 30m, 1h)
- **Multi-Session Analysis**: Weighted scoring system for different trading sessions (Sydney: 0.6x, Tokyo: 0.8x, London: 1.0x, New York: 1.2x)
- **Technical Indicators**: RSI, MACD, and Stochastic analysis for signal confirmation
- **Discord Bot Integration**: Interactive commands (`!start`, `!stop`, `!session`, `!health`) with live-updating signal tables
- **Independent Message Updates**: Multiple tables update independently at their own intervals
- **Volume Filtering**: Minimum volume thresholds to ensure signal quality
- **Configurable Scoring**: Customizable score thresholds for different signal strengths
- **Docker Support**: Ready-to-deploy with Docker and Docker Compose
- **Cloudflare WARP Integration**: Optional DNS over HTTPS for enhanced privacy and reliability
- **Comprehensive Tables**: Professional signal tables with emojis and detailed metrics
- **Session-Based Weighting**: Different importance weights for each trading session
- **Health Monitoring**: Real-time health status of all active scanners
- **Persistent State**: Bot remembers active scanners across restarts using SQLite database
- **Error Handling**: Robust error handling and logging for reliable operation
- **Rate Limiting**: Built-in delays to respect API limits

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
   - ✅ Use Slash Commands (optional, bot works with traditional commands)
   - ✅ Read Message History
   - ✅ Embed Links
   - ✅ Attach Files (for table images)

## 🚀 Quick Start

### Option 1: Docker Deployment (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/imamfahrudin/discord-crypto-vwap-tool.git
   cd discord-crypto-vwap-tool
   ```

2. **Configure the bot**
   ```bash
   # Copy the example env file and edit with your Discord webhook URL
   cp .env.example .env
   nano .env
   ```

3. **Build and run with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **View logs**
   ```bash
   docker-compose logs -f
   ```

#### Docker Features
- **Cloudflare WARP Integration**: Optional DNS over HTTPS for enhanced privacy and reliability
- **Health Checks**: Automatic container health monitoring with DNS connectivity tests
- **Persistent Data**: SQLite database persistence for scanner states across container restarts
- **Timezone Configuration**: Automatic WIB (UTC+7) timezone setting
- **Network Configuration**: Custom bridge network with IPv6 support
- **Privileged Mode**: Required for WARP VPN functionality

#### Environment Variables for Docker
The Docker setup uses the same `.env` file as local deployment. The `USE_WARP` variable controls Cloudflare WARP:
```
USE_WARP=true  # Enable Cloudflare WARP for DNS over HTTPS (recommended for Docker)
```

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
   # Copy and edit the env file
   cp .env.example .env
   # Edit .env with your Discord bot token and other settings
   ```

5. **Run the bot**
   ```bash
   python main.py
   ```

## ⚙️ Configuration

### Environment Variables Setup

Copy the example environment file and customize it:

```bash
cp .env.example .env
```

Then edit `.env` with your settings:

```bash
# Enable Cloudflare WARP for DNS over HTTPS
USE_WARP=true

# Discord Bot Token from https://discord.com/developers/applications
DISCORD_BOT_TOKEN=YOUR_DISCORD_BOT_TOKEN_HERE

# Maximum number of symbols to scan
MAX_SYMBOLS=120

# ⏱️ Refresh intervals in seconds (comma-separated for multiple tables)
# Examples: "120" (single 2m table), "600,1800,3600" (10m, 30m, 1h tables)
REFRESH_INTERVAL=300,900,1800,3600

# Top N symbols to display
TOP_N=15

# Minimum volume to consider valid (in Million USDT)
MIN_VOLUME_M=0.3

# Score thresholds
STRONG_SCORE=80
BUY_SCORE=25
SELL_SCORE=-25
STRONG_SELL_SCORE=-80

# Session weights as JSON object
SESSION_WEIGHTS={"Sydney": 0.6, "Tokyo": 0.8, "London": 1.0, "New York": 1.2}

# Table image footer text (optional - leave empty for no footer)
TABLE_FOOTER_TEXT=

# Embed footer text (optional - leave empty for no footer)
EMBED_FOOTER_TEXT=
```

**Configuration Options:**
- **USE_WARP** (optional): Enable Cloudflare WARP for DNS over HTTPS in Docker. Default: `true`
- **DISCORD_BOT_TOKEN** (required): Your Discord bot token from the Developer Portal
- **MAX_SYMBOLS** (optional): Maximum number of symbols to scan. Default: 120
- **REFRESH_INTERVAL** (optional): Refresh interval(s) in seconds. 
  - Single interval: `"120"` (one table updating every 2 minutes)
  - Multiple intervals: `"600,1800,3600"` (three tables: 10m, 30m, and 1h)
  - When multiple intervals are specified, each gets its own message that updates independently
  - Default: `"300,900,1800,3600"`
- **TOP_N** (optional): Number of top signals to display. Default: 15
- **MIN_VOLUME_M** (optional): Minimum volume in millions USDT. Default: 0.3
- **Score Thresholds**: Customize signal strength thresholds
- **SESSION_WEIGHTS**: Weight different trading sessions as JSON object
- **TABLE_FOOTER_TEXT**: Optional footer text for table images
- **EMBED_FOOTER_TEXT**: Optional footer text for Discord embeds

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

The bot analyzes four major trading sessions with different weights:

- **SYDNEY** (0.6x weight): Sydney trading hours (Australia)
- **TOKYO** (0.8x weight): Tokyo trading hours (Japan)
- **LONDON** (1.0x weight): London trading hours (Europe)
- **NEW YORK** (1.2x weight): New York trading hours (US)

Higher weight sessions have more influence on the final signal score. The bot automatically detects the current active session and may include previous session data for more accurate analysis.

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

### `!session`
- **Description**: Check current session status and trigger manual updates
- **Usage**: Type `!session` to see current session information
- **Behavior**:
  - Shows current active trading session with flag emoji
  - Displays session weight and monitoring status
  - Shows count of active scanners
  - Triggers manual update for all running scanners

### `!health`
- **Description**: Check health status of all active scanners
- **Usage**: Type `!health` to monitor scanner performance
- **Behavior**:
  - Shows status of all active scanner intervals
  - Displays last update times and health indicators
  - Color-coded status: ✅ Healthy, ⚠️ Delayed, ❌ Stale

### Command Permissions
- All commands are available to all users in channels where the bot has message permissions
- The bot must have "Send Messages", "Embed Links", and "Attach Files" permissions in the channel

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
- **Issue**: Missing or invalid .env file
- **Solution**: Ensure `.env` exists and is properly formatted. Copy from `.env.example`

### Docker Issues
- **Issue**: Container fails to start with WARP errors
- **Solution**: Set `USE_WARP=false` in your `.env` file to disable Cloudflare WARP, or ensure privileged mode is enabled in docker-compose.yml
- **Issue**: Health check failures
- **Solution**: Check network connectivity and DNS resolution. The container uses `nslookup` to test connectivity
- **Issue**: Database not persisting between restarts
- **Solution**: Ensure the `bot_data` volume is properly configured in docker-compose.yml
- **Issue**: High CPU usage
- **Solution**: The bot performs parallel processing for multiple exchanges. This is normal behavior during scanning

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
- [Docker](https://www.docker.com/) for containerization
- [Cloudflare WARP](https://1.1.1.1/) for DNS over HTTPS functionality
- [discord.py](https://discordpy.readthedocs.io/) for Discord API integration

## 📧 Contact

**Repository**: [https://github.com/imamfahrudin/discord-crypto-vwap-tool](https://github.com/imamfahrudin/discord-crypto-vwap-tool)

**Issues**: [Report a bug or request a feature](https://github.com/imamfahrudin/discord-crypto-vwap-tool/issues)

---

Made with ❤️ for the crypto trading community