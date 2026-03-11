# Token Launch Alert Bot

Python bot that monitors new token launches via **DexScreener API** and sends **Discord notifications** for tokens with high liquidity (>= $200K).

Supports: **Solana**, **Ethereum**, **Base**, **BSC**

---

## Features

- **Real-time Monitoring** - Polls DexScreener API for new token profiles
- **Multi-chain Support** - Solana, Ethereum, Base, BSC (configurable)
- **Liquidity Filter** - Only alerts for tokens with >= $200K liquidity (configurable)
- **Rich Discord Embeds** - Beautiful notifications with price, liquidity, market cap, volume, DEX info
- **Chain-specific Colors** - Purple for Solana, Blue for Ethereum, Blue for Base, Yellow for BSC
- **Duplicate Prevention** - Tracks seen tokens to avoid duplicate alerts
- **Persistent Storage** - Seen tokens saved to disk, survives restarts
- **Rate Limit Handling** - Auto-retry on Discord rate limits
- **Error Recovery** - Auto-restarts on errors with Discord error notifications
- **Detailed Logging** - File and console logging with configurable levels

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/harismanciripto111/token-alert-bot.git
cd token-alert-bot
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure the bot

Edit `config.py` and set your Discord webhook URL:

```python
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN"
```

**How to get a Discord webhook URL:**
1. Open your Discord server
2. Go to **Server Settings** > **Integrations** > **Webhooks**
3. Click **New Webhook**
4. Choose the channel for alerts
5. Copy the webhook URL

### 4. Run the bot

```bash
python token_alert_bot.py
```

---

## Configuration

All settings are in `config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `DISCORD_WEBHOOK_URL` | (required) | Your Discord webhook URL |
| `MIN_LIQUIDITY_USD` | `200,000` | Minimum liquidity threshold in USD |
| `SUPPORTED_CHAINS` | `solana, ethereum, base, bsc` | Chains to monitor |
| `POLLING_INTERVAL` | `30` | Seconds between API checks |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FILE` | `token_alert_bot.log` | Log file path |

---

## How It Works

1. **Fetch** - Bot polls DexScreener's `/token-profiles/latest/v1` endpoint
2. **Filter** - Checks each token against supported chains
3. **Deduplicate** - Skips tokens already seen (persisted to `seen_tokens.json`)
4. **Enrich** - Fetches pair data with liquidity, price, and volume info
5. **Threshold** - Only proceeds if liquidity >= configured minimum ($200K)
6. **Alert** - Sends rich Discord embed with all token details
7. **Repeat** - Waits for polling interval, then starts again

---

## Discord Alert Example

Each alert includes:
- Token name and symbol
- Current price with 24h change indicator
- Liquidity (USD)
- Market cap / FDV
- 24h trading volume
- Buy/sell transaction counts
- DEX name
- Chain identifier
- Contract address (truncated)
- Pair creation time
- Links to DexScreener and block explorer

---

## API Reference

This bot uses the **DexScreener public API** (free, no authentication required):

- `GET /token-profiles/latest/v1` - Latest token profiles
- `GET /token-pairs/v1/{chainId}/{tokenAddress}` - Token pair data
- `GET /latest/dex/search?q={query}` - Search pairs
- `GET /latest/dex/pairs/{chainId}/{pairAddresses}` - Specific pairs

**Rate Limits:**
- Pair/Search endpoints: 300 requests/minute
- Token profile endpoints: 60 requests/minute

---

## Project Structure

```
token-alert-bot/
├── config.py              # Bot configuration (webhook URL, chains, thresholds)
├── token_alert_bot.py     # Main bot script (DexScreener client, Discord notifier, tracker)
├── requirements.txt       # Python dependencies
├── README.md              # This file
├── AGENT.md               # AI agent context file
├── PLAN.md                # Development plan
└── PROGRESS.md            # Development progress log
```

---

## Running as a Service

To run the bot 24/7 on a Linux server:

```bash
# Using screen
screen -S token-bot
python token_alert_bot.py
# Detach: Ctrl+A, D

# Using nohup
nohup python token_alert_bot.py &

# Using systemd (recommended)
sudo nano /etc/systemd/system/token-alert-bot.service
```

Example systemd service:

```ini
[Unit]
Description=Token Launch Alert Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/token-alert-bot
ExecStart=/usr/bin/python3 token_alert_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## License

MIT

---

## Disclaimer

This bot is for **informational purposes only**. It does not constitute financial advice. Always do your own research (DYOR) before trading any tokens. New token launches carry significant risk including potential rug pulls and scams.
