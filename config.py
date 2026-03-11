# ============================================
# TOKEN LAUNCH ALERT BOT - CONFIGURATION
# ============================================
# Ganti nilai-nilai di bawah sesuai kebutuhan lu

# Discord Webhook URL
# Cara dapetin: Server Settings > Integrations > Webhooks > New Webhook > Copy URL
DISCORD_WEBHOOK_URL = "YOUR_DISCORD_WEBHOOK_URL_HERE"

# Minimum Liquidity Filter (USD)
# Token baru harus punya liquidity minimal segini baru dikirim alert
MIN_LIQUIDITY_USD = 200_000  # $200K

# Supported Chains
# Chain yang mau dimonitor (sesuaikan dengan DexScreener chain IDs)
SUPPORTED_CHAINS = [
    "solana",
    "ethereum",
    "base",
    "bsc",
]

# Polling Interval (seconds)
# Seberapa sering bot ngecek token baru
POLLING_INTERVAL = 30

# DexScreener API Base URL
DEXSCREENER_API_BASE = "https://api.dexscreener.com"

# Alert Settings
ALERT_COLOR_SOLANA = 0x9945FF      # Ungu Solana
ALERT_COLOR_ETHEREUM = 0x627EEA    # Biru Ethereum
ALERT_COLOR_BASE = 0x0052FF        # Biru Base
ALERT_COLOR_BSC = 0xF0B90B         # Kuning BSC
ALERT_COLOR_DEFAULT = 0x00FF88     # Hijau default

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = "token_alert_bot.log"
