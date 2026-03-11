# AGENT.md - Token Launch Alert Bot

## Project Overview
Python bot that monitors new token launches via DexScreener API and sends Discord webhook notifications for tokens meeting a minimum liquidity threshold.

## Tech Stack
- **Language:** Python 3.8+
- **HTTP Client:** requests
- **API:** DexScreener public API (free, no auth)
- **Notifications:** Discord webhooks with rich embeds
- **Storage:** JSON file for seen token tracking

## Key Files
- `config.py` - All configurable settings (webhook URL, chains, thresholds)
- `token_alert_bot.py` - Main bot with DexScreener client, Discord notifier, token tracker
- `requirements.txt` - Python dependencies

## Architecture
- `DexScreenerClient` - Handles all API calls to DexScreener
- `DiscordNotifier` - Formats and sends Discord webhook embeds
- `TokenTracker` - Tracks seen tokens to prevent duplicate alerts
- `TokenAlertBot` - Main orchestrator that runs the monitoring loop

## Important Notes
- DexScreener API rate limit: 300 req/min (pairs), 60 req/min (profiles)
- Discord webhook rate limit: handled with auto-retry on 429
- Seen tokens persisted to `seen_tokens.json` (max 10,000 entries)
- Bot runs indefinitely until Ctrl+C, auto-recovers from errors
