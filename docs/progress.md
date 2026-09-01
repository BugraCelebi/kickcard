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
- [x] Reconnect + outage resilience (yayın 6 saat sürüyor)
- [x] `economy/ledger.py` — balance changes + ledger entries, negative balance guard
- [x] Activity window and per-stream cap
  - [x] Bot hesaplarını eddie kazanımından dışla (BotRix vb. — liste `EDDIE_EXCLUDED_USERNAMES`
    ortam değişkeninden, `economy/activity.py` tarafından okunuyor)
- [ ] `!eddie` command + chat reply
- [ ] **Bir yayın boyunca sessizce çalıştır, `ledger_entry` tablosunu incele**
  - [x] `tests/economy/test_ledger_reconciliation.py` — bir oyuncu için `ledger_entry` toplamı
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
- [ ] Abonelik / takip / hediye abonelik WS olaylarını parse et (ekonomi kazanım kalemleri)
  Payload şekli ve kanal adı bilinmiyor — `chatrooms.{id}.v2` değil, muhtemelen
  `channel.{channel_id}`. Canlı yayında ham JSON yakalanmalı; `.env`'e numerik channel id
  değişkeni gerekecek.
- [ ] Stream modes + `!mod` + vault mechanic
  - [ ] Yetki kontrolü için `sender.identity.badges` alanını ingest'te `ChatMessage`'a taşı
    (broadcaster/moderator rozeti)
  - [ ] `!mod` ile canlı moda ilk geçişte `start_stream_session()` tetiklensin — aynı yayın
    içindeki mod değişimleri (GAME→SILENT→GAME) yeni oturum BAŞLATMAMALI, yoksa tavan sıfırlanır.
    `scripts/start_session.py` ve `scripts/set_mode.py` aynı primitifleri (`start_stream_session()`,
    `set_stream_mode()`) çağırıyor; `!mod` da bunları kullansın, mantığı kopyalamasın
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
- [ ] Test boilerplate'ini `conftest.py`'ye çıkar (`_run`, `_connect_pg`, `_insert_test_player`
  üç dosyada tekrarlanıyor)

## Sprint 4 — Balance

- [ ] Aktiflik kazanç oranı ile per-stream cap'i uyumlu hale getir — mevcut sabitlerle 400 tavanına
  3.3 saat gerekiyor (5 dk'da 10 eddie = 120/saat), `plan.md` §4.5 ise 2 saatlik yayında ~400
  varsayıyor (gerçekte maks. 240); paket fiyatlandırması bu rakama dayanıyor. Karar Sprint 1'in
  `tests/economy/test_simulation.py` sonucundan sonra.
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
  **Güncelleme:** kullanıcı bağlantı/ping-pong/basit reconnect'i canlı Kick trafiğinde doğruladı —
  varsayımlar doğru çıktı.
- 2026-08-31: Reconnect + outage resilience eklendi: exponential backoff (full jitter),
  `ConnectionState` (`CONNECTING`/`CONNECTED`/`RECONNECTING`) gözlemlenebilirliği, `open_timeout`,
  outage penceresi loglama. **Bu davranış (backoff büyümesi, stabil bağlantı sonrası sıfırlanma,
  outage log'ları) henüz gerçek bir kesintiyle canlı doğrulanmadı** — sadece saf
  `compute_backoff_delay` fonksiyonu test edildi.
- 2026-09-01: Bot entrypoint hazır (`src/kickcard/bot/main.py` + `scripts/start_session.py`,
  `scripts/set_mode.py`). Çalıştırma sırası README'de: session → mod → bot. Bot Kick'e hiçbir şey
  yazmıyor. **Bu sırada bulunup düzeltilen sessiz hata:** `run_activity_granter` uzun ömürlü tek
  bir bağlantı alıyordu; `upsert_player`'ın açtığı örtük transaction hiç commit edilmiyordu (credit'in
  `conn.transaction()`'ı içine SAVEPOINT olarak giriyordu), yani hiçbir eddie kalıcılaşmıyordu ve
  6 saat açık kalan bir transaction oluşuyordu. Testler yakalayamamıştı çünkü kasten rollback edip
  aynı bağlantıdan okuyorlar. Granter artık tick başına kendi bağlantısını açıyor (context manager
  çıkışta commit ediyor), DB kesintisinden sonra kendiliğinden toparlanıyor, ve 3 ardışık
  başarısızlıkta `error` seviyesine yükseliyor. Ayrı bir `psql` bağlantısından doğrulandı.
- 2026-09-01: Aktiflik penceresi + tavan eklendi (`economy/activity.py`, `store/stream_session.py`,
  `store/player.py`). Sıcak yol (her mesaj) sadece 2 Redis yazması; DB işleri 5 dk'lık tick'te.
  Session **tembel oluşturulmuyor** — Redis restart'ında tavanın sıfırlanıp herkesin ikinci kez 400
  kazanması geri alınamaz olurdu; session yoksa tick hiç ödül vermiyor. 7 entegrasyon testi gerçek
  Redis+Postgres'e karşı geçti. `economy/` strict mypy kapsamında olduğu için redis-py'nin
  `Awaitable[T] | T` dönüş tipine karşı küçük bir `_redis_call` yardımcısı gerekti.
- 2026-08-31: `economy/ledger.py` (`credit`/`debit`, `Currency`, `InsufficientBalanceError`,
  `PlayerNotFoundError`) ve `store/db.py` (`get_pg_connection`, async psycopg) eklendi.
  `tests/economy/test_ledger.py` gerçek docker-compose Postgres'ine karşı çalışıp geçti (6 canlı
  entegrasyon testi dahil — nested-transaction/SAVEPOINT varsayımı da doğrulandı).
  **Platform notu:** Windows'ta async psycopg, varsayılan `ProactorEventLoop` altında
  `psycopg.InterfaceError` fırlatıyor; `asyncio.run(..., loop_factory=lambda:
  asyncio.SelectorEventLoop(selectors.SelectSelector()))` gerekiyor. Bunu testte çözdük ama
  `bot/`/`api/` entrypoint'leri yazılırken (Postgres'e dokunan her async giriş noktası) aynı
  sorun tekrar çıkacak — o zaman hatırlanmalı.
