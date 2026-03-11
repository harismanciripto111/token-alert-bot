#!/usr/bin/env python3
"""
============================================
TOKEN LAUNCH ALERT BOT
============================================
Bot Python yang monitor token baru via DexScreener API
dan kirim notifikasi Discord untuk token dengan
liquidity tinggi (>= $200K).

Supported chains: Solana, Ethereum, Base, BSC

Usage:
    python token_alert_bot.py

Author: Token Alert Bot
Version: 1.0.0
"""

import time
import json
import logging
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

import requests

from config import (
    DISCORD_WEBHOOK_URL,
    MIN_LIQUIDITY_USD,
    SUPPORTED_CHAINS,
    POLLING_INTERVAL,
    DEXSCREENER_API_BASE,
    ALERT_COLOR_SOLANA,
    ALERT_COLOR_ETHEREUM,
    ALERT_COLOR_BASE,
    ALERT_COLOR_BSC,
    ALERT_COLOR_DEFAULT,
    LOG_LEVEL,
    LOG_FILE,
)

# ============================================
# LOGGING SETUP
# ============================================

def setup_logging() -> logging.Logger:
    """Configure logging with both file and console handlers."""
    logger = logging.getLogger("TokenAlertBot")
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    # File handler
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_fmt)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(console_fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


logger = setup_logging()


# ============================================
# DEXSCREENER API CLIENT
# ============================================

class DexScreenerClient:
    """Client for interacting with DexScreener API."""

    def __init__(self, base_url: str = DEXSCREENER_API_BASE):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "TokenAlertBot/1.0",
        })

    def get_latest_token_profiles(self) -> List[Dict]:
        """Fetch latest token profiles from DexScreener.

        Returns:
            List of token profile dicts.
        """
        url = f"{self.base_url}/token-profiles/latest/v1"
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                return data
            return []
        except requests.exceptions.Timeout:
            logger.warning("DexScreener API timeout for token profiles")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"DexScreener API error (token profiles): {e}")
            return []
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from DexScreener token profiles")
            return []

    def get_token_pairs(self, chain_id: str, token_address: str) -> List[Dict]:
        """Fetch pairs for a specific token on a chain.

        Args:
            chain_id: The chain identifier (e.g., 'solana', 'ethereum').
            token_address: The token contract address.

        Returns:
            List of pair dicts with price, liquidity, volume data.
        """
        url = f"{self.base_url}/token-pairs/v1/{chain_id}/{token_address}"
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                return data
            return []
        except requests.exceptions.Timeout:
            logger.warning(f"DexScreener API timeout for {chain_id}/{token_address}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"DexScreener API error (pairs): {e}")
            return []
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from DexScreener pairs")
            return []

    def search_pairs(self, query: str) -> List[Dict]:
        """Search for pairs by token name, symbol, or address.

        Args:
            query: Search query string.

        Returns:
            List of matching pair dicts.
        """
        url = f"{self.base_url}/latest/dex/search"
        try:
            response = self.session.get(url, params={"q": query}, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data.get("pairs", [])
        except requests.exceptions.Timeout:
            logger.warning(f"DexScreener API timeout for search: {query}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"DexScreener API error (search): {e}")
            return []
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from DexScreener search")
            return []

    def get_pairs_by_chain(self, chain_id: str, pair_addresses: List[str]) -> List[Dict]:
        """Fetch specific pairs by their addresses on a chain.

        Args:
            chain_id: The chain identifier.
            pair_addresses: List of pair contract addresses.

        Returns:
            List of pair dicts.
        """
        if not pair_addresses:
            return []
        addresses = ",".join(pair_addresses[:30])  # API limit
        url = f"{self.base_url}/latest/dex/pairs/{chain_id}/{addresses}"
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data.get("pairs", []) if isinstance(data, dict) else []
        except requests.exceptions.RequestException as e:
            logger.error(f"DexScreener API error (pairs by chain): {e}")
            return []
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from DexScreener pairs by chain")
            return []


# ============================================
# DISCORD NOTIFIER
# ============================================

class DiscordNotifier:
    """Sends rich embed notifications to Discord via webhook."""

    def __init__(self, webhook_url: str = DISCORD_WEBHOOK_URL):
        self.webhook_url = webhook_url
        self.session = requests.Session()

    def _get_chain_color(self, chain_id: str) -> int:
        """Get embed color based on chain."""
        colors = {
            "solana": ALERT_COLOR_SOLANA,
            "ethereum": ALERT_COLOR_ETHEREUM,
            "base": ALERT_COLOR_BASE,
            "bsc": ALERT_COLOR_BSC,
        }
        return colors.get(chain_id.lower(), ALERT_COLOR_DEFAULT)

    def _get_chain_emoji(self, chain_id: str) -> str:
        """Get emoji representation for chain."""
        emojis = {
            "solana": "\u2600\ufe0f",
            "ethereum": "\u2b1c",
            "base": "\U0001f535",
            "bsc": "\U0001f7e1",
        }
        return emojis.get(chain_id.lower(), "\U0001f4a0")

    def _get_chain_explorer_url(self, chain_id: str, address: str) -> str:
        """Get block explorer URL for a token address."""
        explorers = {
            "solana": f"https://solscan.io/token/{address}",
            "ethereum": f"https://etherscan.io/token/{address}",
            "base": f"https://basescan.org/token/{address}",
            "bsc": f"https://bscscan.com/token/{address}",
        }
        return explorers.get(chain_id.lower(), "#")

    def _format_number(self, value: float) -> str:
        """Format large numbers with K/M/B suffixes."""
        if value is None:
            return "N/A"
        if value >= 1_000_000_000:
            return f"${value / 1_000_000_000:.2f}B"
        if value >= 1_000_000:
            return f"${value / 1_000_000:.2f}M"
        if value >= 1_000:
            return f"${value / 1_000:.2f}K"
        return f"${value:.2f}"

    def _format_price(self, price: Optional[str]) -> str:
        """Format token price string."""
        if price is None:
            return "N/A"
        try:
            p = float(price)
            if p < 0.00001:
                return f"${p:.10f}"
            if p < 0.01:
                return f"${p:.6f}"
            if p < 1:
                return f"${p:.4f}"
            return f"${p:.2f}"
        except (ValueError, TypeError):
            return "N/A"

    def _truncate(self, text: str, max_len: int = 40) -> str:
        """Truncate text with ellipsis if too long."""
        if len(text) <= max_len:
            return text
        return text[: max_len - 3] + "..."

    def send_token_alert(self, token_data: Dict, pair_data: Dict) -> bool:
        """Send a rich embed Discord alert for a new token.

        Args:
            token_data: Token profile data from DexScreener.
            pair_data: Best pair data with liquidity info.

        Returns:
            True if sent successfully, False otherwise.
        """
        if self.webhook_url == "YOUR_DISCORD_WEBHOOK_URL_HERE":
            logger.warning("Discord webhook URL not configured! Set DISCORD_WEBHOOK_URL in config.py")
            return False

        chain_id = token_data.get("chainId", "unknown")
        token_address = token_data.get("tokenAddress", "N/A")
        chain_emoji = self._get_chain_emoji(chain_id)
        chain_color = self._get_chain_color(chain_id)
        explorer_url = self._get_chain_explorer_url(chain_id, token_address)

        # Extract pair data
        base_token = pair_data.get("baseToken", {})
        token_name = base_token.get("name", "Unknown Token")
        token_symbol = base_token.get("symbol", "???")
        price_usd = pair_data.get("priceUsd")
        liquidity = pair_data.get("liquidity", {})
        liquidity_usd = liquidity.get("usd", 0)
        volume_24h = pair_data.get("volume", {}).get("h24", 0)
        price_change_24h = pair_data.get("priceChange", {}).get("h24", 0)
        market_cap = pair_data.get("marketCap") or pair_data.get("fdv", 0)
        pair_url = pair_data.get("url", f"https://dexscreener.com/{chain_id}/{token_address}")
        dex_id = pair_data.get("dexId", "Unknown DEX")
        pair_created = pair_data.get("pairCreatedAt")
        txns = pair_data.get("txns", {})
        txns_24h = txns.get("h24", {})
        buys_24h = txns_24h.get("buys", 0)
        sells_24h = txns_24h.get("sells", 0)

        # Format created time
        created_str = "N/A"
        if pair_created:
            try:
                created_dt = datetime.fromtimestamp(pair_created / 1000, tz=timezone.utc)
                created_str = created_dt.strftime("%Y-%m-%d %H:%M UTC")
            except (ValueError, TypeError, OSError):
                created_str = "N/A"

        # Price change indicator
        if price_change_24h and price_change_24h > 0:
            price_indicator = f"\u2b06\ufe0f +{price_change_24h:.2f}%"
        elif price_change_24h and price_change_24h < 0:
            price_indicator = f"\u2b07\ufe0f {price_change_24h:.2f}%"
        else:
            price_indicator = "\u27a1\ufe0f 0.00%"

        # Token icon
        icon_url = token_data.get("icon", "")
        if not icon_url:
            header = token_data.get("header", "")
            icon_url = header if header else None

        # Build embed
        embed = {
            "title": f"{chain_emoji} NEW TOKEN: {self._truncate(token_name)} ({token_symbol})",
            "description": (
                f"**A new token with high liquidity has been detected on {chain_id.upper()}!**\n\n"
                f"\U0001f4ca [View on DexScreener]({pair_url}) | "
                f"\U0001f50d [View on Explorer]({explorer_url})"
            ),
            "color": chain_color,
            "fields": [
                {
                    "name": "\U0001f4b0 Price",
                    "value": f"{self._format_price(price_usd)}\n{price_indicator}",
                    "inline": True,
                },
                {
                    "name": "\U0001f4a7 Liquidity",
                    "value": self._format_number(liquidity_usd),
                    "inline": True,
                },
                {
                    "name": "\U0001f4c8 Market Cap",
                    "value": self._format_number(market_cap),
                    "inline": True,
                },
                {
                    "name": "\U0001f4ca 24h Volume",
                    "value": self._format_number(volume_24h),
                    "inline": True,
                },
                {
                    "name": "\U0001f4b1 24h Txns",
                    "value": f"Buys: {buys_24h} | Sells: {sells_24h}",
                    "inline": True,
                },
                {
                    "name": "\U0001f3e6 DEX",
                    "value": dex_id.replace("_", " ").title(),
                    "inline": True,
                },
                {
                    "name": "\u26d3\ufe0f Chain",
                    "value": chain_id.upper(),
                    "inline": True,
                },
                {
                    "name": "\U0001f4dd Contract",
                    "value": f"`{token_address[:8]}...{token_address[-6:]}`" if len(token_address) > 14 else f"`{token_address}`",
                    "inline": True,
                },
                {
                    "name": "\u23f0 Pair Created",
                    "value": created_str,
                    "inline": True,
                },
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "footer": {
                "text": "Token Alert Bot | DexScreener API",
            },
        }

        # Add token icon if available
        if icon_url:
            embed["thumbnail"] = {"url": icon_url}

        # Build payload
        payload = {
            "username": "Token Alert Bot",
            "embeds": [embed],
        }

        try:
            response = self.session.post(
                self.webhook_url,
                json=payload,
                timeout=10,
            )
            if response.status_code == 204:
                logger.info(f"Alert sent: {token_symbol} on {chain_id} (Liq: {self._format_number(liquidity_usd)})")
                return True
            elif response.status_code == 429:
                retry_after = response.json().get("retry_after", 5)
                logger.warning(f"Discord rate limited. Retry after {retry_after}s")
                time.sleep(retry_after)
                return self.send_token_alert(token_data, pair_data)
            else:
                logger.error(f"Discord webhook error: {response.status_code} - {response.text[:200]}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Discord webhook request failed: {e}")
            return False

    def send_startup_message(self) -> bool:
        """Send a startup notification to Discord."""
        if self.webhook_url == "YOUR_DISCORD_WEBHOOK_URL_HERE":
            logger.warning("Discord webhook URL not configured!")
            return False

        chains_str = ", ".join(c.upper() for c in SUPPORTED_CHAINS)
        embed = {
            "title": "\U0001f680 Token Alert Bot Started",
            "description": (
                f"Bot is now monitoring new token launches!\n\n"
                f"**Chains:** {chains_str}\n"
                f"**Min Liquidity:** ${MIN_LIQUIDITY_USD:,.0f}\n"
                f"**Polling Interval:** {POLLING_INTERVAL}s"
            ),
            "color": ALERT_COLOR_DEFAULT,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "footer": {"text": "Token Alert Bot"},
        }

        payload = {"username": "Token Alert Bot", "embeds": [embed]}

        try:
            response = self.session.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code == 204
        except requests.exceptions.RequestException:
            return False

    def send_error_message(self, error_msg: str) -> bool:
        """Send an error notification to Discord."""
        if self.webhook_url == "YOUR_DISCORD_WEBHOOK_URL_HERE":
            return False

        embed = {
            "title": "\u26a0\ufe0f Token Alert Bot Error",
            "description": f"```{error_msg[:1900]}```",
            "color": 0xFF0000,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "footer": {"text": "Token Alert Bot"},
        }

        payload = {"username": "Token Alert Bot", "embeds": [embed]}

        try:
            response = self.session.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code == 204
        except requests.exceptions.RequestException:
            return False


# ============================================
# TOKEN TRACKER
# ============================================

class TokenTracker:
    """Tracks seen tokens to avoid duplicate alerts."""

    SEEN_TOKENS_FILE = "seen_tokens.json"
    MAX_SEEN_TOKENS = 10_000

    def __init__(self):
        self.seen_tokens: Set[str] = set()
        self._load_seen_tokens()

    def _get_token_key(self, chain_id: str, token_address: str) -> str:
        """Generate unique key for a token."""
        raw = f"{chain_id.lower()}:{token_address.lower()}"
        return hashlib.md5(raw.encode()).hexdigest()

    def is_seen(self, chain_id: str, token_address: str) -> bool:
        """Check if a token has already been seen."""
        key = self._get_token_key(chain_id, token_address)
        return key in self.seen_tokens

    def mark_seen(self, chain_id: str, token_address: str) -> None:
        """Mark a token as seen."""
        key = self._get_token_key(chain_id, token_address)
        self.seen_tokens.add(key)

        # Prevent unbounded growth
        if len(self.seen_tokens) > self.MAX_SEEN_TOKENS:
            excess = len(self.seen_tokens) - self.MAX_SEEN_TOKENS
            to_remove = list(self.seen_tokens)[:excess]
            for item in to_remove:
                self.seen_tokens.discard(item)

        self._save_seen_tokens()

    def _load_seen_tokens(self) -> None:
        """Load seen tokens from disk."""
        try:
            with open(self.SEEN_TOKENS_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    self.seen_tokens = set(data)
                else:
                    self.seen_tokens = set()
            logger.info(f"Loaded {len(self.seen_tokens)} seen tokens from disk")
        except FileNotFoundError:
            logger.info("No seen tokens file found, starting fresh")
            self.seen_tokens = set()
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error loading seen tokens: {e}")
            self.seen_tokens = set()

    def _save_seen_tokens(self) -> None:
        """Save seen tokens to disk."""
        try:
            with open(self.SEEN_TOKENS_FILE, "w") as f:
                json.dump(list(self.seen_tokens), f)
        except IOError as e:
            logger.error(f"Error saving seen tokens: {e}")

    def get_stats(self) -> Dict:
        """Get tracker statistics."""
        return {
            "total_seen": len(self.seen_tokens),
            "max_capacity": self.MAX_SEEN_TOKENS,
        }


# ============================================
# MAIN BOT
# ============================================

class TokenAlertBot:
    """Main bot that orchestrates monitoring and alerting."""

    def __init__(self):
        self.dex_client = DexScreenerClient()
        self.discord = DiscordNotifier()
        self.tracker = TokenTracker()
        self.total_alerts_sent = 0
        self.total_tokens_scanned = 0
        self.start_time = datetime.now(timezone.utc)

    def _filter_pair(self, pair: Dict) -> bool:
        """Check if a pair meets the liquidity threshold.

        Args:
            pair: Pair data dict from DexScreener.

        Returns:
            True if pair meets minimum liquidity requirement.
        """
        liquidity = pair.get("liquidity", {})
        liquidity_usd = liquidity.get("usd", 0) if isinstance(liquidity, dict) else 0

        if liquidity_usd is None:
            return False

        return float(liquidity_usd) >= MIN_LIQUIDITY_USD

    def _get_best_pair(self, pairs: List[Dict]) -> Optional[Dict]:
        """Get the best pair (highest liquidity) from a list.

        Args:
            pairs: List of pair dicts.

        Returns:
            Best pair dict or None.
        """
        valid_pairs = [p for p in pairs if self._filter_pair(p)]
        if not valid_pairs:
            return None

        return max(
            valid_pairs,
            key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0),
        )

    def _process_token(self, token_data: Dict) -> bool:
        """Process a single token profile.

        Args:
            token_data: Token profile data from DexScreener.

        Returns:
            True if alert was sent, False otherwise.
        """
        chain_id = token_data.get("chainId", "").lower()
        token_address = token_data.get("tokenAddress", "")

        # Skip unsupported chains
        if chain_id not in SUPPORTED_CHAINS:
            return False

        # Skip already seen tokens
        if self.tracker.is_seen(chain_id, token_address):
            return False

        self.total_tokens_scanned += 1

        # Fetch pair data for this token
        pairs = self.dex_client.get_token_pairs(chain_id, token_address)
        if not pairs:
            # Mark as seen even without pairs to avoid re-checking
            self.tracker.mark_seen(chain_id, token_address)
            return False

        # Find best pair meeting liquidity threshold
        best_pair = self._get_best_pair(pairs)
        if not best_pair:
            self.tracker.mark_seen(chain_id, token_address)
            return False

        # Send alert
        success = self.discord.send_token_alert(token_data, best_pair)
        self.tracker.mark_seen(chain_id, token_address)

        if success:
            self.total_alerts_sent += 1
            token_symbol = best_pair.get("baseToken", {}).get("symbol", "???")
            liq = best_pair.get("liquidity", {}).get("usd", 0)
            logger.info(
                f"New token alert: {token_symbol} on {chain_id.upper()} "
                f"(Liquidity: ${liq:,.0f})"
            )

        return success

    def _run_cycle(self) -> int:
        """Run a single monitoring cycle.

        Returns:
            Number of alerts sent in this cycle.
        """
        alerts_this_cycle = 0

        # Fetch latest token profiles
        profiles = self.dex_client.get_latest_token_profiles()
        if not profiles:
            logger.debug("No new token profiles found")
            return 0

        logger.debug(f"Fetched {len(profiles)} token profiles")

        for token_data in profiles:
            try:
                if self._process_token(token_data):
                    alerts_this_cycle += 1
                    # Small delay between alerts to respect Discord rate limits
                    time.sleep(1)
            except Exception as e:
                chain_id = token_data.get("chainId", "unknown")
                addr = token_data.get("tokenAddress", "unknown")
                logger.error(f"Error processing token {chain_id}/{addr}: {e}")
                continue

        return alerts_this_cycle

    def run(self) -> None:
        """Main bot loop. Runs continuously until interrupted."""
        chains_str = ", ".join(c.upper() for c in SUPPORTED_CHAINS)

        logger.info("="*50)
        logger.info("TOKEN LAUNCH ALERT BOT")
        logger.info("="*50)
        logger.info(f"Monitoring chains: {chains_str}")
        logger.info(f"Min liquidity: ${MIN_LIQUIDITY_USD:,.0f}")
        logger.info(f"Polling interval: {POLLING_INTERVAL}s")
        logger.info(f"Seen tokens: {self.tracker.get_stats()['total_seen']}")
        logger.info("="*50)

        # Send startup notification
        self.discord.send_startup_message()

        cycle_count = 0

        while True:
            try:
                cycle_count += 1
                logger.debug(f"Starting cycle #{cycle_count}")

                alerts = self._run_cycle()

                if alerts > 0:
                    logger.info(f"Cycle #{cycle_count}: {alerts} alert(s) sent")
                else:
                    logger.debug(f"Cycle #{cycle_count}: no new tokens")

                # Log periodic stats
                if cycle_count % 60 == 0:
                    uptime = datetime.now(timezone.utc) - self.start_time
                    stats = self.tracker.get_stats()
                    logger.info(
                        f"Stats | Uptime: {uptime} | "
                        f"Cycles: {cycle_count} | "
                        f"Alerts sent: {self.total_alerts_sent} | "
                        f"Tokens scanned: {self.total_tokens_scanned} | "
                        f"Seen tokens: {stats['total_seen']}"
                    )

                time.sleep(POLLING_INTERVAL)

            except KeyboardInterrupt:
                logger.info("Bot stopped by user (Ctrl+C)")
                break
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
                self.discord.send_error_message(str(e))
                logger.info(f"Retrying in {POLLING_INTERVAL * 2}s...")
                time.sleep(POLLING_INTERVAL * 2)

        # Shutdown
        logger.info("="*50)
        logger.info("BOT SHUTDOWN")
        logger.info(f"Total alerts sent: {self.total_alerts_sent}")
        logger.info(f"Total tokens scanned: {self.total_tokens_scanned}")
        logger.info(f"Seen tokens: {self.tracker.get_stats()['total_seen']}")
        logger.info("="*50)


# ============================================
# ENTRY POINT
# ============================================

if __name__ == "__main__":
    bot = TokenAlertBot()
    bot.run()
