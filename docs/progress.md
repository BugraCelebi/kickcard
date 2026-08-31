<!-- TARGET PATH: <project root>/docs/progress.md -->

# Progress

Bir madde bitince kutuyu işaretle. Yeni oturuma başlarken önce bu dosyayı oku.
Bir madde 30 dakikadan uzun sürüyorsa alt maddelere böl.

## Sprint 0 — Foundation (yayında değil)

- [x] Project skeleton, `make dev/test/lint`, ruff + mypy config
- [x] Postgres schema + migration (`player`, `collection`, `deck`, `duel`, `ledger_entry`)
  - [x] Migration'ı gerçek bir Postgres'e karşı çalıştır ve şemayı doğrula
    (`docker compose up -d && uv run --env-file .env python scripts/migrate.py`).
- [x] Redis connection, stream mode key
- [x] `src/kickcard/ingest/` — Pusher WS connection, raw message -> `ChatMessage`
  - [ ] Abonelik / takip / hediye abonelik WS olaylarını parse et (ekonomi kazanım kuralları
    bunlara bağlı)
- [ ] Reconnect + outage resilience (yayın 6 saat sürüyor)
- [ ] `economy/ledger.py` — balance changes + ledger entries, negative balance guard
- [ ] Activity window and per-stream cap
- [ ] `!eddie` command + chat reply
- [ ] **Bir yayın boyunca sessizce çalıştır, `ledger_entry` tablosunu incele**
  - [ ] `tests/economy/test_ledger_reconciliation.py` — bir oyuncu için `ledger_entry` toplamı
    (eddies ve dust ayrı ayrı) `player.eddies` / `player.dust` ile eşleşiyor mu, test et

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
  - [ ] Yetki kontrolü için `sender.identity.badges` alanını ingest'te `ChatMessage`'a taşı
    (broadcaster/moderator rozeti)
- [ ] Chat hygiene: silent on success, 60s batched summary, global throttle
- [ ] **Yayında duyur — ilk gerçek test**

## Sprint 2 — Duels

- [ ] `src/game/engine.py` — pure function returning `TurnLog`
- [ ] Edge case tests (see `.claude/rules/game-engine.md`)
- [ ] `!deste` (with codes) + `!deste oto`
- [ ] `!düello` / `!kabul` + 60s timeout
- [ ] Overlay: turn-by-turn playback, core bars
- [ ] Match records -> `duel` table

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

- 2026-08-30: Proje iskeleti kuruldu. `Makefile` yerine doğrudan `uv run pytest/ruff/mypy` kullanılıyor
  (bu ortamda `make` yok); paketler tek çatı paket `src/kickcard/{ingest,bot,game,economy,store,api}`
  altında. `docs/card-game-plan.md` → `docs/plan.md` olarak yeniden adlandırıldı. `CLAUDE.md` ve
  `.claude/rules/` içindeki yollar buna göre güncellendi.
- 2026-08-31: Docker bu oturumda kullanılabilir hale geldi (önceki oturumlarda yoktu).
  `docker compose up -d` + `uv run --env-file .env python scripts/migrate.py` çalıştırıldı;
  `\d` ile `player`/`collection`/`deck`/`duel`/`ledger_entry` şeması ve tüm adlandırılmış CHECK
  constraint'leri canlı Postgres'te doğrulandı, `schema_migrations` kaydı mevcut. Redis container'ı
  da `PONG` ile doğrulandı.
- 2026-08-31: `src/kickcard/ingest/` (Pusher WS → `ChatMessage`) eklendi. **Gerçek bir Kick hesabına
  karşı doğrulanmadı** — bu ortamda canlı bir Kick yayını/token yok. `parse_chat_message`'daki chat
  mesajı payload şeması (alan adları, `sender.identity`/`badges` yapısı) ve `pusher:subscribe`'ın
  `socket_id` olmadan çalıştığı varsayımı, gerçek trafikte teyit edilmeli. Sorun çıkarsa düzeltme
  tek dosyada kalır: `src/kickcard/ingest/pusher_client.py`.
