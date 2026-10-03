<!-- TARGET PATH: <project root>/docs/progress.md -->

# Progress

Bir madde bitince kutuyu işaretle. Yeni oturuma başlarken önce bu dosyayı oku.
Bir madde 30 dakikadan uzun sürüyorsa alt maddelere böl.

## Sprint 0 — Foundation (yayında değil)

- [x] Project skeleton, `uv run pytest / ruff / mypy`, ruff + mypy config
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
- [ ] `!eddie` command + chat reply — Sprint 0'dan taşındı: chat'e yazmayı gerektiriyor
  (Kick write-client Sprint 1'de), ayrıca sessiz toplama döneminde kimse bakiyesini
  sorgulayamamalı
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

## Sprint 1'e taşınan notlar

Öğrenme sürecinde çıkan, başka yerde kayıtlı olmayan maddeler.

Paket satın alma kısıtları: bkz. `.claude/rules/rules-economy.md`.

**Bilinen ve kabul edilmiş davranış:**

- `grant_activity_eddies` içinde Redis'teki `activity_earned` sayacı Postgres commit'inden önce
  artıyor. Tick ortasında hata olursa Postgres geri alınıyor, Redis alınmıyor; ilgili oyuncunun
  yayın tavanı en fazla 10 eddie erken doluyor. Hata eksik ödeme yönünde, ledger ile bakiye
  tutarlı kalıyor. Şimdilik düzeltme yok.

**Karar bekleyen:**

- `!kayıt` gibi Türkçe karakterli komut adları: Python `"KAYIT".lower()` sonucu
  `"kayit"`, `"kayıt"` değil. Komut eşleştirmesinde nasıl normalize edileceği komut
  katmanı yazılırken kararlaştırılmalı.

**Test boşlukları:**

- [ ] `test_activity.py` yeni `activity_capped` sayacının arttığını ve özet logun basıldığını
  kontrol etmiyor.
- [ ] `debit` için sıfır miktar ve `credit` için boş sebep testleri yok gibi görünüyor; mutasyon
  ile doğrulanmalı.

Operasyon kuralları: bkz. `CLAUDE.md`.

## Sprint 2 — Duels

- [ ] `src/game/engine.py` — pure function returning `TurnLog`
- [ ] Edge case tests (see `.claude/rules/rules-game-engine.md`)
- [ ] `!deste` (with codes) + `!deste oto`
- [ ] `!düello` / `!kabul` + 60s timeout
- [ ] Overlay: turn-by-turn playback, core bars
- [ ] Match records -> `duel` table

## Sprint 3 — Polish

- [ ] Dust + `!craft`
- [ ] `!sıralama` + stream closing scene
- [ ] Anti-abuse: account age threshold, first 3 messages earn nothing
- [ ] `BUSY` mode auto-trigger
- [ ] En az bir ledger testi commit sonrası AYRI bir bağlantıdan okusun — mevcut testler
  rollback + aynı bağlantı deseni kullanıyor, bu desen sessiz commit hatalarını yapısal
  olarak göremiyor (Sprint 0 entrypoint'inde bulunan bug tam olarak buydu)
- [ ] Test boilerplate'ini `conftest.py`'ye çıkar (`_run`, `_connect_pg`, `_insert_test_player`
  üç dosyada tekrarlanıyor)
- [ ] Session bazlı Redis anahtarlarına TTL koy (48 saat) — `activity`, `activity_usernames`,
  `activity_earned` her yayında yeni anahtar üretiyor, eskiler süresiz birikiyor. Kalıcı veri
  zaten Postgres'te, Redis'te sadece güncel yayın durmalı.

## Sprint 4 — Balance

- [x] Per-stream activity cap 400'den 500'e çıkarıldı (`economy/activity.py`,
  `.claude/rules/rules-economy.md`, `plan.md` §4.1/§4.5). Gerekçe: yayınlar tipik 4.5-5 saat (54-60 tick)
  sürüyor; 400 tavanı 3s20'de doluyor ve en sadık izleyiciyi son 1-1.5 saati ödülsüz bırakıyordu.
  500 = 4s10, tavan hâlâ devrede ama artık ortalama izleyiciyi hedefleyen bir denge aracı değil,
  en üstteki farm koruması.
- [ ] Tavan 500'e çıkarıldıktan sonra 2-3 yayın daha ölç — kaç kişi tavana ulaşıyor, kaç tick boşa
  gidiyor (activity_capped sayacı).
- [ ] Card win-rate report from match data
- [ ] Second eddie sink
- [ ] Duel reward / wager (deferred earlier)
- [ ] 15-card expansion set

## Bilinen riskler

Sprint 0'dan devreden, henüz çözülmemiş riskler.

1. **Kick realtime altyapısı değişmiş.** Tarayıcı artık
   `wss://realtime.us-east-1.platform.kick.com/connection/websocket` adresine bağlanıyor. Zarf
   yapısı Pusher formatından farklı (`push`/`pub`/`channel`/`tags` sarmalayıcıları var). Bot hâlâ
   eski Pusher endpoint'inde (`ws-us2.pusher.com`) ve iki canlı yayında sorunsuz çalıştı, ancak
   eski endpoint habersiz kapatılabilir. Ingest sınırı sayesinde geçiş maliyeti tek dosya
   (`pusher_client.py`) ve `ChatMessage` tipi değişmez. 2026-09-20 tarihinde tarayıcı trafiği
   incelenerek tespit edildi.
2. **Sessizlik tespiti yok.** Bağlantı açık olduğu halde uzun süre hiç chat mesajı gelmemesi
   durumunu yakalayan bir kontrol yok. WS ping/pong bunu kapatmıyor: boru açık kalır, akış durur,
   loglar temiz görünür. `received_any_message` bayrağı sadece bağlantı koptuktan sonra backoff
   sayacını sıfırlamak için okunuyor, çalışma sırasında sessizliği izlemiyor. Yukarıdaki endpoint
   riskiyle birleştiğinde "sessizce ölen bot" senaryosu mümkün. Sprint 1'de karar verilmeli: eşik
   süresi ne olmalı ve uyarı nereye gitmeli (chat hijyeni kuralı chat'e yazmayı engelliyor).

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
- 2026-08-31: `src/kickcard/ingest/` (Pusher WS → `ChatMessage`) eklendi. `parse_chat_message`'daki
  chat mesajı payload şeması (alan adları, `sender.identity`/`badges` yapısı) ve `pusher:subscribe`'ın
  `socket_id` olmadan çalıştığı varsayımdı; **kullanıcı bunları canlı Kick trafiğinde doğruladı —
  varsayımlar doğru çıktı.** Sorun çıkarsa düzeltme tek dosyada kalır:
  `src/kickcard/ingest/pusher_client.py`.
- 2026-08-31: Reconnect + outage resilience eklendi: exponential backoff (full jitter),
  `ConnectionState` (`CONNECTING`/`CONNECTED`/`RECONNECTING`) gözlemlenebilirliği, `open_timeout`,
  outage penceresi loglama. **Canlı doğrulandı:** kesinti sırasında backoff attempt 0'dan 5'e
  büyüdü, 60s tavanına oturdu, stabil bağlantı sonrası sıfırlandı; `open_timeout` DNS hatasında
  devreye girdi; outage süresi doğru loglandı.
- 2026-08-31: `economy/ledger.py` (`credit`/`debit`, `Currency`, `InsufficientBalanceError`,
  `PlayerNotFoundError`) ve `store/db.py` (`get_pg_connection`, async psycopg) eklendi.
  `tests/economy/test_ledger.py` gerçek docker-compose Postgres'ine karşı çalışıp geçti (6 canlı
  entegrasyon testi dahil — nested-transaction/SAVEPOINT varsayımı da doğrulandı).
  **Platform notu:** Windows'ta async psycopg, varsayılan `ProactorEventLoop` altında
  `psycopg.InterfaceError` fırlatıyor; `asyncio.run(..., loop_factory=lambda:
  asyncio.SelectorEventLoop(selectors.SelectSelector()))` gerekiyor. Bunu testte çözdük ama
  `bot/`/`api/` entrypoint'leri yazılırken (Postgres'e dokunan her async giriş noktası) aynı
  sorun tekrar çıkacak — o zaman hatırlanmalı.
- 2026-09-01: Aktiflik penceresi + tavan eklendi (`economy/activity.py`, `store/stream_session.py`,
  `store/player.py`). Sıcak yol (her mesaj) sadece 2 Redis yazması; DB işleri 5 dk'lık tick'te.
  Session **tembel oluşturulmuyor** — Redis restart'ında tavanın sıfırlanıp herkesin ikinci kez 400
  kazanması geri alınamaz olurdu; session yoksa tick hiç ödül vermiyor. 7 entegrasyon testi gerçek
  Redis+Postgres'e karşı geçti. `economy/` strict mypy kapsamında olduğu için redis-py'nin
  `Awaitable[T] | T` dönüş tipine karşı küçük bir `_redis_call` yardımcısı gerekti.
- 2026-09-01: Bot entrypoint hazır (`src/kickcard/bot/main.py` + `scripts/start_session.py`,
  `scripts/set_mode.py`). Çalıştırma sırası README'de: session → mod → bot. Bot Kick'e hiçbir şey
  yazmıyor. **Bu sırada bulunup düzeltilen sessiz hata:** `run_activity_granter` uzun ömürlü tek
  bir bağlantı alıyordu; `upsert_player`'ın açtığı örtük transaction hiç commit edilmiyordu (credit'in
  `conn.transaction()`'ı içine SAVEPOINT olarak giriyordu), yani hiçbir eddie kalıcılaşmıyordu ve
  6 saat açık kalan bir transaction oluşuyordu. Testler yakalayamamıştı çünkü kasten rollback edip
  aynı bağlantıdan okuyorlar. Granter artık tick başına kendi bağlantısını açıyor (context manager
  çıkışta commit ediyor), DB kesintisinden sonra kendiliğinden toparlanıyor, ve 3 ardışık
  başarısızlıkta `error` seviyesine yükseliyor. Ayrı bir `psql` bağlantısından doğrulandı.
