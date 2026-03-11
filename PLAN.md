# PLAN.md - Token Launch Alert Bot

## Goal
Build a Python bot that monitors new token launches across multiple chains and sends Discord alerts for tokens with significant liquidity.

## Phase 1: Core Bot (DONE)
- [x] DexScreener API client with error handling and timeouts
- [x] Discord webhook notifier with rich embeds
- [x] Token tracker with duplicate prevention (JSON persistence)
- [x] Main bot loop with configurable polling interval
- [x] Multi-chain support: Solana, Ethereum, Base, BSC
- [x] Liquidity threshold filter (>= $200K default)
- [x] Chain-specific embed colors and emojis
- [x] Block explorer links per chain
- [x] Rate limit handling for Discord webhooks
- [x] Error recovery with auto-restart
- [x] File + console logging

## Phase 2: Enhancements (TODO)
- [ ] Add more chains (Arbitrum, Polygon, Avalanche)
- [ ] Token security scoring / rug pull detection
- [ ] Volume spike alerts for existing tokens
- [ ] Configurable alert filters (min market cap, min volume)
- [ ] Multiple Discord webhook support (different channels per chain)
- [ ] Web dashboard for monitoring bot status
- [ ] Database backend (SQLite) instead of JSON file
- [ ] Telegram bot integration as alternative to Discord

## Phase 3: Advanced (TODO)
- [ ] WebSocket streaming instead of polling
- [ ] Machine learning for token quality scoring
- [ ] Integration with DEXTools and Birdeye APIs
- [ ] Automated trading signals
- [ ] Portfolio tracking
