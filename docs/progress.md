<!-- TARGET PATH: <project root>/docs/progress.md -->

# Progress

Bir madde bitince kutuyu işaretle. Yeni oturuma başlarken önce bu dosyayı oku.
Bir madde 30 dakikadan uzun sürüyorsa alt maddelere böl.

## Sprint 0 — Foundation (yayında değil)

- [ ] Project skeleton, `make dev/test/lint`, ruff + mypy config
- [ ] Postgres schema + migration (`player`, `collection`, `deck`, `match`, `ledger_entry`)
- [ ] Redis connection, stream mode key
- [ ] `src/ingest/` — Pusher WS connection, raw message -> `Command`
- [ ] Reconnect + outage resilience (yayın 6 saat sürüyor)
- [ ] `economy/ledger.py` — balance changes + ledger entries, negative balance guard
- [ ] Activity window and per-stream cap
- [ ] `!eddie` command + chat reply
- [ ] **Bir yayın boyunca sessizce çalıştır, `ledger_entry` tablosunu incele**

## Sprint 1 — Cards and packs

- [ ] `data/cards.json` — 30 cards with codes
- [ ] `tests/game/test_budget.py` — budget formula check
- [ ] Card HTML/CSS component (typographic, no illustrations)
- [ ] `PackOpener` — slot structure, pity, atomic transaction
- [ ] `tests/economy/test_simulation.py` — 1000 players, 5 streams
- [ ] `!kayıt` -> starter deck + 3 free packs
- [ ] `!paket`, `!koleksiyon`, `!kart` + fuzzy matching
- [ ] Overlay: WebSocket connection, scene manager, queue
- [ ] Overlay: pack opening animation
- [ ] Stream modes + `!mod` + vault mechanic
- [ ] Chat hygiene: silent on success, 60s batched summary, global throttle
- [ ] **Yayında duyur — ilk gerçek test**

## Sprint 2 — Duels

- [ ] `src/game/engine.py` — pure function returning `TurnLog`
- [ ] Edge case tests (see `.claude/rules/game-engine.md`)
- [ ] `!deste` (with codes) + `!deste oto`
- [ ] `!düello` / `!kabul` + 60s timeout
- [ ] Overlay: turn-by-turn playback, core bars
- [ ] Match records -> `match` table

## Sprint 3 — Polish

- [ ] Dust + `!craft`
- [ ] `!sıralama` + stream closing scene
- [ ] Anti-abuse: account age threshold, first 3 messages earn nothing
- [ ] `BUSY` mode auto-trigger

## Sprint 4 — Balance

- [ ] Card win-rate report from match data
- [ ] Second eddie sink
- [ ] Duel reward / wager (deferred earlier)
- [ ] 15-card expansion set

## Notes

<!-- Oturum sonlarında öğrendiklerini buraya yaz. Tekrarlayan bir düzeltme
     görürsen CLAUDE.md'ye veya ilgili rule dosyasına taşı. -->
