# Kickcard — Öğrenme Yolu

Bu belge, kickcard'da kullandığımız her teknolojiyi ve verdiğimiz her kararı öğrenmen için
hazırlandı. Sırayla git; her modül bir öncekine dayanıyor.

---

## Nasıl çalışacaksın

**Üç kural:**

1. **Her modül bir şey yaparak biter.** Okuyup anlamak yanılsama üretir. Bir şeyi bozup
   düzeltmek gerçek öğrenmedir. Her modülün sonundaki alıştırmayı atlama.
2. **Bozmaktan korkma.** Yerel veritabanı tek komutla sıfırlanıyor:
   `docker compose down -v && docker compose up -d && uv run --env-file .env python scripts/migrate.py`
   Git de her şeyi geri alıyor: `git checkout -- .`
   **Dikkat:** bu iki komut geri alınamaz. `git checkout -- .` commit edilmemiş tüm değişiklikleri,
   `docker compose down -v` veritabanındaki tüm veriyi siler. Sadece commit edilmemiş gerçek iş
   yokken ve veritabanında korunacak veri yokken güvenlidir.
3. **Anlamadığın yerde dur.** "Sonra anlarım" diye geçme; bu yığında her katman bir öncekine
   dayanıyor, boşluk büyüyerek ilerliyor.

**İki kaynağı farklı işler için kullan:**

| Soru tipi | Nereye |
|---|---|
| "Bu dosya ne yapıyor", "bu fonksiyon nereden çağrılıyor" | Claude Code — dosyaları okuyabiliyor |
| "Neden böyle yaptık", "şunu değiştirsem ne olur", "X kavramı nedir" | Bu sohbet — kararların gerekçesi burada |

**Claude Code'a soru sorma kalıbı:**

> `<dosya yolu>` dosyasını aç ve bana satır satır anlat. Python'da yeniyim, kullanılan
> kavramları da açıkla. Kod yazma, sadece anlat.

**Süre:** her modül 45-90 dakika. Toplam 10 modül. Günde bir modül iyi bir tempo —
aralarda Sprint 1'e devam et, çünkü asıl öğrenme yeni kod yazarken oluyor.

---

## Modül 1 — Proje iskeleti: uv, paketler, komutlar

### Kavramlar

- **Paket yöneticisi nedir** — `uv` ne yapıyor, `pip`'ten farkı ne
- **`pyproject.toml`** — projenin kimlik kartı: bağımlılıklar, Python sürümü, araç ayarları
- **`uv.lock`** — neden ayrı bir dosya, neden commit ediliyor
- **Sanal ortam (`.venv`)** — neden global Python'a kurmuyoruz
- **src-layout** — `src/kickcard/` neden `kickcard/` değil
- **`__init__.py`** — bir klasörü Python paketi yapan şey
- **Import yolu** — `from kickcard.economy.ledger import credit` nasıl çözülüyor

### Kickcard'da nerede

`pyproject.toml`, `.python-version`, `src/kickcard/__init__.py`, `src/kickcard/ingest/__init__.py`

### Oku

```
pyproject.toml
src/kickcard/ingest/__init__.py
```

İkincisi 3 satır ama önemli: `ingest`'in dışarıya ne sunduğunu tanımlıyor. `__all__` listesi
"bu paketten şunlar alınabilir" demek — bir sınır çizgisi.

### Yap

1. `uv run python -c "import kickcard; print(kickcard.__file__)"` çalıştır. Paketin nerede
   olduğunu gör.
2. `pyproject.toml`'daki `line-length = 100` değerini 60 yap, `uv run ruff check .` çalıştır.
   Onlarca hata göreceksin. Geri al.
3. `src/kickcard/economy/__init__.py`'yi aç. `__all__` listesinden `debit`'i sil,
   `uv run pytest` çalıştır. Ne kırıldı? Neden?

### Kendini test et

- `uv run pytest` ile `pytest` arasındaki fark ne?
- `pyproject.toml`'daki `[dependency-groups] dev` neden `[project] dependencies`'ten ayrı?
- Yeni bir modül eklesen (`src/kickcard/game/engine.py`), onu import etmek için başka bir şey
  yapman gerekir mi?

---

## Modül 2 — Docker ve iki veritabanı

### Kavramlar

- **Container nedir** — sanal makineden farkı, neden hafif
- **`docker-compose.yml`** — birden fazla servisi tek dosyada tanımlamak
- **Port eşleme** (`5432:5432`) — soldaki host, sağdaki container
- **Volume** — container silinince verinin kaybolmaması
- **Neden hem Postgres hem Redis** — bu, projenin en önemli mimari kararlarından biri

### Postgres vs Redis — neden ikisi birden

| | Postgres | Redis |
|---|---|---|
| Veri nerede | Diskte | Bellekte |
| Hız | Milisaniye | Mikrosaniye |
| Kaybolursa | Felaket | Tolere edilebilir |
| Kickcard'da ne tutuyor | Bakiye, ledger, koleksiyon | Aktiflik penceresi, mod, session |

Ayrımın mantığı: **her chat mesajında** Redis'e yazıyoruz (saniyede 15 mesaj olabilir),
**5 dakikada bir** Postgres'e yazıyoruz. Her mesajda Postgres'e yazsaydık veritabanı boğulurdu.

Ama Redis kaybolabilir — bu yüzden orada sadece "geçici" veri var. Bakiye asla Redis'te
tutulmuyor.

### Oku

```
docker-compose.yml
.env.example
```

### Yap

1. `docker compose ps` — iki servis çalışıyor mu?
2. `docker compose exec redis redis-cli PING` → `PONG` almalısın
3. `docker compose exec postgres psql -U kickcard -d kickcard -c "\dt"` → tabloları listele
4. `docker compose restart redis` çalıştır, sonra
   `docker compose exec redis redis-cli KEYS "*"` — anahtarlar duruyor mu?
   (Redis'te varsayılan olarak diske yazma açık, o yüzden duruyor olabilir — ama
   güvenilmemesi gereken bir şey.)
5. `docker compose down` (volume silmeden) sonra `up -d` — Postgres verisi duruyor mu?

### Kendini test et

- `docker compose down` ile `docker compose down -v` arasındaki fark ne? Hangisi tehlikeli?
- `.env` ile `.env.example` neden ayrı? Hangisi git'e giriyor?
- Bakiyeyi Redis'te tutsaydık ne olurdu?

---

## Modül 3 — Postgres: şema, kısıtlar, migration

### Kavramlar

- **Tablo, satır, kolon** — temel
- **Primary key** — her satırı benzersiz kılan şey
- **Foreign key** — tablolar arası bağ; `ledger_entry.kick_user_id` neden `player`'a bağlı
- **CHECK constraint** — veritabanı seviyesinde kural
- **NULL** — "değer yok"; `duel.winner` neden nullable (berabere)
- **Index** — neden `ledger_entry(kick_user_id, created_at)` üzerinde var
- **JSONB** — yapılandırılmış veriyi tek kolonda tutmak
- **Migration** — şemayı sürüm sürüm değiştirmek, geri alınabilirlik

### Neden CHECK constraint'ler var

Kodda zaten `InsufficientBalanceError` kontrolü var. Peki neden veritabanında da
`CHECK (eddies >= 0)` var?

**Çünkü kod hata yapabilir.** Yarın biri `ledger.py`'yi atlayıp doğrudan `UPDATE` yazarsa,
veritabanı onu reddediyor. Buna *savunma derinliği* deniyor: aynı kuralı birden fazla
katmanda uygulamak.

### Oku

```
db/migrations/0001_initial_schema.sql
scripts/migrate.py
```

İkincisi 45 satır ve tamamı anlaşılabilir — kendi yazdığımız minik bir migration runner.
`schema_migrations` tablosunun ne işe yaradığına dikkat et.

### Yap

1. Şemayı incele:
   ```bash
   docker compose exec postgres psql -U kickcard -d kickcard -c "\d player"
   docker compose exec postgres psql -U kickcard -d kickcard -c "\d ledger_entry"
   ```
2. Kısıtları bozmayı dene (hepsi reddedilmeli):
   ```sql
   INSERT INTO player (kick_user_id, username, eddies) VALUES (999, 'test', -5);
   INSERT INTO ledger_entry (kick_user_id, kind, currency, amount, reason)
     VALUES (999, 'test', 'gold', 10, 'x');
   ```
   Hata mesajlarındaki kısıt adlarını oku — bu yüzden onları isimlendirmiştik.
3. **Kendi migration'ını yaz.** `db/migrations/0002_add_player_note.sql` oluştur:
   ```sql
   ALTER TABLE player ADD COLUMN note TEXT;
   ```
   Çalıştır: `uv run --env-file .env python scripts/migrate.py`
   Sonra `\d player` ile gör. İkinci kez çalıştır — "No pending migrations" demeli.
   Sonra dosyayı sil ve DB'yi sıfırla.

### Kendini test et

- `schema_migrations` tablosu olmasaydı ne olurdu?
- `collection.card_id` neden foreign key değil? (İpucu: kartlar nerede yaşıyor?)
- `deck.card_ids` neden JSONB, neden ayrı bir tablo değil?

---

## Modül 4 — async/await

**Bu modül en önemlisi.** Kodun her yerinde geçiyor ve anlamadan devam edilemez.

### Kavramlar

- **Eşzamanlılık (concurrency) nedir** — aynı anda birden fazla işi *beklemek*
- **Blocking vs non-blocking** — `time.sleep(5)` ile `await asyncio.sleep(5)` farkı
- **Coroutine** — `async def` ile tanımlanan fonksiyon; çağırınca çalışmaz, `await` gerekir
- **Event loop** — coroutine'leri sırayla çalıştıran motor
- **`await`** — "bu işi bekle, bu sırada başka işler çalışsın"
- **Task** — arka planda çalışan coroutine
- **`asyncio.TaskGroup`** — birden fazla task'ı birlikte yönetmek
- **Async generator** — `yield` içeren `async def`; sonsuz veri akışı
- **`GeneratorExit`** — generator kapatılırken fırlatılan özel istisna
- **`CancelledError`** — task iptal edilirken fırlatılan istisna

### Neden async

Bot aynı anda iki şey yapıyor: Kick'ten mesaj dinliyor **ve** 5 dakikada bir eddie dağıtıyor.
Normal (senkron) kodda bunlardan biri diğerini bloke ederdi. `await` sayesinde biri
beklerken diğeri çalışıyor.

### Kickcard'da yaşadığımız gerçek hata

`pusher_client.py`'de bir zamanlar şöyle bir kod vardı:

```python
try:
    async with websockets.connect(...) as ws:
        async for raw in ws:
            yield message
finally:
    await asyncio.sleep(5)     # ← HATA
```

`finally` bloğu generator **her çıkışında** çalışıyor — kapatılırken de. Kapatma sırasında
Python `GeneratorExit` fırlatıyor, ve o sırada `await` etmek yasak:
`RuntimeError: async generator ignored GeneratorExit`.

Çözüm: `sleep`'i `finally`'den çıkarıp döngünün sonuna almak.

Bu hatayı anlamak, async'i anlamış olmanın iyi bir testi.

### Oku

```
src/kickcard/bot/main.py
src/kickcard/ingest/pusher_client.py
```

`main.py` kısa ve `TaskGroup` kullanımının net bir örneği. `pusher_client.py`'deki
`messages()` fonksiyonu ise async generator'ın gerçek bir kullanımı.

### Yap

1. Küçük bir deney dosyası yaz (`scratch_async.py`, commit etme):
   ```python
   import asyncio, time

   async def yavas(ad, saniye):
       print(f"{ad} basladi")
       await asyncio.sleep(saniye)
       print(f"{ad} bitti")

   async def main():
       basla = time.time()
       async with asyncio.TaskGroup() as tg:
           tg.create_task(yavas("A", 2))
           tg.create_task(yavas("B", 2))
       print(f"toplam {time.time() - basla:.1f}s")

   asyncio.run(main())
   ```
   Kaç saniye sürdü? Neden 4 değil?
2. `await asyncio.sleep(2)` yerine `time.sleep(2)` yaz. Şimdi kaç saniye? Neden?
3. `bot/main.py`'de `TaskGroup` yerine sadece `await run_activity_granter(client)` yaz
   (chat tüketicisini çıkar). Bot hâlâ çalışır mı? Ne kaybettin?

### Kendini test et

- `async def` bir fonksiyonu `await` olmadan çağırırsan ne olur?
- `TaskGroup` içindeki bir task hata fırlatırsa diğerine ne olur? Bunu neden istedik?
- Neden `bot/main.py` Windows'ta özel bir event loop kullanıyor?

---

## Modül 5 — WebSocket ve Kick bağlantısı

### Kavramlar

- **HTTP vs WebSocket** — istek/cevap ile sürekli açık bağlantı farkı
- **Pusher protokolü** — Kick'in kullandığı mesajlaşma katmanı
- **Kanal (channel)** ve subscribe — `chatrooms.37904423.v2`
- **Ping/pong** — bağlantının canlı tutulması
- **Yeniden bağlanma (reconnect)** — kopan bağlantıyı kurtarmak
- **Exponential backoff** — her denemede daha uzun bekleme
- **Jitter** — beklemeye rastgelelik katmak, neden
- **`open_timeout`** — bağlantı kurulurken sonsuza kadar asılı kalmamak
- **At-most-once teslimat** — kesinti sırasındaki mesajlar kalıcı olarak kaybolur

### Neden backoff ve jitter

Bağlantı koptu. Hemen tekrar denesen, sunucu hâlâ kapalıysa saniyede yüzlerce deneme
yaparsın — IP ban yersin. Bu yüzden her başarısızlıkta bekleme süresi katlanıyor:
1s, 2s, 4s, 8s... 60 saniyede tavanlanıyor.

Jitter ise bekleme süresine rastgelelik katıyor. Tek istemcide önemi az ama binlerce
istemci aynı anda bağlanmaya çalışırsa hepsi aynı saniyede denemesin diye.

### Sınır kuralı — projenin en önemli mimari kararlarından

`src/kickcard/ingest/` dışına **hiçbir Kick'e özgü tip çıkmıyor**. Ham JSON içeride
`ChatMessage` nesnesine çevriliyor, dışarıya sadece o gidiyor.

Sebep: Kick resmi olmayan bir endpoint kullanıyoruz ve bir gün değişecek. O gün geldiğinde
sadece `pusher_client.py` değişecek, geri kalan kod hiç etkilenmeyecek.

### Oku

```
src/kickcard/ingest/chat_message.py    (10 satır, çok basit ama önemli)
src/kickcard/ingest/pusher_client.py   (asıl iş burada)
```

### Yap

1. Tarayıcıda Kick kanalını aç, F12 → Network → WS. Gerçek trafiği gör.
   `ChatMessageEvent` payload'unu bul, `parse_chat_message`'ın hangi alanları aldığını
   karşılaştır.
2. `scratch_listen.py` yaz (Modül sonunda sil):
   ```python
   import asyncio, logging
   from kickcard.ingest import KickIngestClient

   logging.basicConfig(level=logging.INFO)

   async def main():
       async for m in KickIngestClient().messages():
           print(f"{m.username}: {m.text}")

   asyncio.run(main())
   ```
3. Çalışırken Wi-Fi'ı kes. Backoff'un büyümesini izle. Geri aç, `reconnected after Xs
   outage` satırını gör.
4. `.env`'deki `KICK_PUSHER_WS_URL`'i bozuk bir adresle değiştir. `open_timeout`'un
   devreye girdiğini gör.

### Kendini test et

- `ChatMessage`'a `badges` alanı eklesek sınır kuralını ihlal etmiş olur muyuz?
- Kesinti sırasında yazılan mesajlar neden kurtarılamıyor?
- `parse_chat_message` neden ayrı bir fonksiyon, neden sınıfın içinde değil?

---

## Modül 6 — Redis: veri tipleri ve aktiflik penceresi

### Kavramlar

- **Key-value store** — anahtar/değer deposu
- **Veri tipleri:** String, HASH, ZSET (sorted set)
- **ZSET** — her üyenin bir skoru var, skora göre aralık sorgulanabilir
- **Namespace** — `kickcard:activity:{session}` gibi ikinokta ile gruplama
- **Atomik komutlar** — `HINCRBY` neden "oku, artır, yaz"dan güvenli

### Aktiflik penceresi neden ZSET

Soru şu: "son 10 dakikada kim mesaj yazdı?"

ZSET'te üye = kullanıcı id, skor = son mesaj zamanı. `ZRANGEBYSCORE key (şimdi-600) +inf`
tek komutta cevabı veriyor. Ve `ZREMRANGEBYSCORE` ile eski kayıtlar temizleniyor.

Bunu bir listede tutsaydın her seferinde tüm listeyi taraman gerekirdi.

### Üç anahtar ne işe yarıyor

| Anahtar | Tip | İçerik |
|---|---|---|
| `kickcard:activity:{session}` | ZSET | kim ne zaman yazdı |
| `kickcard:activity_usernames:{session}` | HASH | user_id → kullanıcı adı |
| `kickcard:activity_earned:{session}` | HASH | user_id → bu yayında kazanılan |

Üçü de session id'ye bağlı — yeni yayın = yeni anahtarlar = tavan sıfırlanmış.

### Oku

```
src/kickcard/store/redis_client.py     (çok kısa)
src/kickcard/store/stream_mode.py
src/kickcard/store/stream_session.py
src/kickcard/economy/activity.py       (asıl iş)
```

### Yap

1. Redis'i elle keşfet:
   ```bash
   docker compose exec redis redis-cli KEYS "kickcard:*"
   docker compose exec redis redis-cli TYPE "kickcard:activity:<session>"
   docker compose exec redis redis-cli ZRANGE "kickcard:activity:<session>" 0 -1 WITHSCORES
   docker compose exec redis redis-cli HGETALL "kickcard:activity_earned:<session>"
   ```
2. Kendin bir ZSET oluştur ve oyna:
   ```bash
   docker compose exec redis redis-cli ZADD deneme 100 ali 200 veli 300 ayse
   docker compose exec redis redis-cli ZRANGEBYSCORE deneme 150 +inf
   docker compose exec redis redis-cli DEL deneme
   ```
3. Mod anahtarını elle değiştir, botun davranışını gör:
   ```bash
   docker compose exec redis redis-cli SET kickcard:stream_mode SILENT
   ```
   Sonra `GAME`'e geri al.
4. Mod anahtarına saçma bir değer yaz (`redis-cli SET kickcard:stream_mode SACMA`).
   Bot ne yapıyor? Neden `OFF`'a düşüyor?

### Kendini test et

- Session id kaybolursa neden yeni bir tane oluşturmuyoruz?
- `activity_earned` neden HASH, neden ayrı ayrı String değil?
- Redis'teki tüm veriyi silsen bakiyeler kaybolur mu?

---

## Modül 7 — Transaction ve ledger

**Bu modül ekonominin kalbi.** Buradaki hatalar sessizce para kaybettiriyor.

### Kavramlar

- **Transaction** — ya hepsi olur ya hiçbiri (atomiklik)
- **COMMIT / ROLLBACK**
- **Örtük (implicit) transaction** — psycopg'de ilk sorguyla otomatik açılan
- **SAVEPOINT** — transaction içinde transaction
- **Yarış koşulu (race condition)** — iki işlemin aynı veriyi aynı anda değiştirmesi
- **Koşullu UPDATE** — `WHERE eddies >= %s` ile atomik kontrol
- **Ledger (defter) deseni** — her değişikliği kaydetmek, bakiyeyi türetebilmek

### Neden ledger

Bakiyeyi doğrudan değiştirsek, "bu kişi neden 340 eddie'ye sahip" sorusunu asla
cevaplayamazdık. Ledger her hareketi kaydediyor: ne zaman, ne kadar, neden.

Ve bu bir denetim aracı: `SUM(ledger_entry.amount)` her zaman `player.eddies`'e eşit
olmalı. Eşit değilse birisi kuralı atlamış.

### Yarış koşulu ve çözümü

İki kişi aynı anda paket alsa:

```
İşlem A: bakiye oku (150) → yeterli → 100 düş → yaz (50)
İşlem B: bakiye oku (150) → yeterli → 100 düş → yaz (50)
```

Sonuç: 200 eddie harcandı ama bakiye 50. Kayıp.

Çözüm — okuma ve yazmayı tek atomik komutta yapmak:

```sql
UPDATE player SET eddies = eddies - 100
WHERE kick_user_id = %s AND eddies >= 100
```

Etkilenen satır 0 ise bakiye yetersizdi. Postgres bu tek ifadeyi atomik çalıştırıyor.

### Kickcard'da yaşadığımız gerçek hata

Granter uzun ömürlü tek bir bağlantı kullanıyordu. `upsert_player` örtük bir transaction
açıyor, `credit()`'in kendi transaction'ı içine SAVEPOINT olarak giriyor, ve **dıştaki
transaction hiç commit edilmiyordu.** Yani hiçbir eddie kalıcı olmuyordu.

Testler yakalayamadı çünkü hepsi kasten rollback edip **aynı bağlantıdan** okuyor.
Hata ancak ayrı bir `psql` bağlantısından bakınca göründü.

Ders: "veri yazıldı" ile "veri kalıcı oldu" farklı şeyler.

### Oku

```
src/kickcard/economy/ledger.py
src/kickcard/store/db.py
tests/economy/test_ledger.py
```

### Yap

1. Elle bir transaction dene:
   ```bash
   docker compose exec postgres psql -U kickcard -d kickcard
   ```
   ```sql
   BEGIN;
   INSERT INTO player (kick_user_id, username) VALUES (999, 'deneme');
   SELECT * FROM player WHERE kick_user_id = 999;   -- görünüyor
   ROLLBACK;
   SELECT * FROM player WHERE kick_user_id = 999;   -- yok
   ```
2. İki terminalden aynı anda transaction aç, ikisinde de aynı satırı güncelle. İkincisi
   bekliyor mu? Neden?
3. **Mutabakatı bozup düzelt:**
   ```sql
   UPDATE player SET eddies = eddies + 999 WHERE kick_user_id = <senin_id>;
   ```
   `uv run --env-file .env pytest tests/economy/test_ledger_reconciliation.py -v`
   Kırmızı olmalı. Hata mesajı ne diyor? Sonra geri al:
   ```sql
   UPDATE player SET eddies = eddies - 999 WHERE kick_user_id = <senin_id>;
   ```
   Test yeşile dönmeli.

### Kendini test et

- `debit` neden hata fırlatmadan önce transaction'ın **içinde** kalıyor?
- Granter neden tick başına yeni bağlantı açıyor?
- `ledger_entry.reason` neden boş olamıyor?

---

## Modül 8 — Test stratejisi

### Kavramlar

- **pytest** — test bulma, çalıştırma, raporlama
- **Saf fonksiyon testi vs entegrasyon testi**
- **`pytest.skip`** — ortam yoksa testi atlamak, kırmak değil
- **Test izolasyonu** — testlerin birbirini etkilememesi
- **Negatif kontrol** — dedektörün gerçekten dedekte ettiğini kanıtlamak
- **Mutasyon kontrolü** — kodu bilerek bozup testin kırıldığını görmek

### Neden bazı testler gerçek veritabanı kullanıyor

Mock'lamak (sahte nesne kullanmak) hızlı ama yalan söyleyebilir. `credit()`'in gerçekten
çalıştığını ancak gerçek Postgres'e yazıp okuyarak bilirsin. SAVEPOINT davranışını mock
ile test etmek imkânsız.

Karşılığında testler biraz yavaş ve Docker gerektiriyor — bu yüzden `pytest.skip` var.

### Negatif kontrol neden var

`test_reconciliation_detects_a_balance_changed_outside_the_ledger` testi, ledger'ı atlayarak
bakiyeyi değiştirip dedektörün bunu **bulduğunu** doğruluyor.

Bu olmasaydı: sorguda bir hata olsa (hep boş dönse), diğer testler yeşil kalırdı ve
invariant'ı hiç korumamış olurduk.

### Oku

```
tests/economy/test_ledger_reconciliation.py
tests/ingest/test_pusher_client.py
tests/store/test_stream_mode.py
```

Üçü farklı test tipini gösteriyor: entegrasyon, saf fonksiyon, ve parametreli test.

### Yap

1. `uv run pytest -v` — tüm testleri gör
2. `uv run pytest -k ledger -v` — sadece isminde "ledger" geçenler
3. `uv run pytest tests/economy/test_ledger.py::test_credit_rejects_non_positive_amount -v`
   — tek test
4. **Mutasyon testi yap:** `ledger.py`'de `if amount <= 0:` satırını `if amount < 0:` yap.
   Hangi test kırıldı? Geri al.
5. **Kendi testini yaz.** `tests/store/test_stream_session.py` oluştur ve session id'nin
   `start_stream_session` çağrıldığında değiştiğini doğrula.

### Kendini test et

- Neden `parse_chat_message` test edilebiliyor ama `messages()` edilemiyor?
- Bir test `SKIPPED` görünüyorsa endişelenmeli misin?
- "Test kırmızıysa kod yanlıştır" kuralının istisnası olabilir mi?

---

## Modül 9 — Kod kalitesi araçları

### Kavramlar

- **Linter (`ruff`)** — stil ve olası hata tespiti
- **Type hints** — `def f(x: int) -> str:`
- **`mypy`** — tip kontrolü; çalıştırmadan hata bulma
- **`strict` mod** — neden sadece `game/` ve `economy/` üzerinde
- **`StrEnum`** — sabit değer kümesi; neden çıplak string'den iyi

### Neden strict mypy sadece iki pakette

`game/` ve `economy/` hata yaparsa **sessizce yanlış sonuç** üretiyor — düello yanlış
biter, bakiye yanlış hesaplanır, ve kimse fark etmez. Diğer paketlerde hata genelde
gürültülü (bağlantı kopar, exception fırlar).

Sıkılığı en çok gereken yere koyduk.

### Oku

`pyproject.toml`'daki `[tool.ruff]` ve `[tool.mypy]` bölümleri.

### Yap

1. `uv run ruff check .` — temiz mi?
2. `ledger.py`'de bir fonksiyonun dönüş tipini kaldır (`-> None` sil).
   `uv run mypy src` ne diyor?
3. `Currency.EDDIES` yerine `"eddies"` string'i yaz. mypy yakalıyor mu?
4. Kullanılmayan bir import ekle (`import os`). `ruff` ne diyor?

### Kendini test et

- Type hints çalışma zamanında bir şey yapıyor mu?
- `StrEnum` yerine düz string kullansak ne kaybederdik?
- `ruff` ile `mypy` aynı şeyleri mi buluyor?

---

## Modül 10 — Tasarım ilkeleri

Bu modül kod okumuyor, **kararları** okuyor. Öncekilerin hepsi bittikten sonra yap.

### İlkeler

**1. Asimetrik maliyet.** Bir varsayılan her iki yönde de yanlış olabiliyorsa, hatası geri
alınabilir olanı seç.
- Mod anahtarı yoksa → `OFF` (yanlışlıkla yayına çıkmaktansa sessiz kal)
- Session yoksa → hiç ödül verme (tavanı sıfırlamaktansa bir tick kaybet)

**2. Saflık (purity).** `game/` motoru dış dünyaya dokunmuyor. Aynı girdi her zaman aynı
çıktıyı veriyor. Bu, test edilebilirliğin ve tekrar oynatılabilirliğin temeli.

**3. Bağımlılık enjeksiyonu.** `PackOpener(rng)`, `credit(conn, ...)` — nesneler kendi
bağımlılıklarını yaratmıyor, dışarıdan alıyor. Testlerde sahte/kontrollü versiyonlar
geçilebiliyor.

**4. Sınır kuralı.** Kick'e özgü tipler `ingest/` dışına çıkmıyor. Bir gün Kick API'sı
değişince tek dosya değişecek.

**5. Tek doğruluk kaynağı.** Kart verileri `data/cards.json`'da, bakiye değişimleri
`ledger.py`'de, durum kaydı `docs/progress.md`'de. Aynı bilgi iki yerde yaşamıyor.

**6. Savunma derinliği.** Aynı kural hem kodda hem veritabanında. `InsufficientBalanceError`
kontrolü **ve** `CHECK (eddies >= 0)`.

### Oku

```
CLAUDE.md
.claude/rules/economy.md
.claude/rules/game-engine.md
.claude/rules/bot-overlay.md
docs/plan.md
```

### Yap

Her ilke için projeden **iki örnek** bul. Bulamadığın varsa sor — ya ilke uygulanmamış,
ya da bir şeyi kaçırıyorsun.

Sonra tersini dene: bu ilkelerden birini ihlal eden bir tasarım öner ve neyin bozulacağını
anlat.

### Kendini test et

- Neden `game/` motoru rastgeleliği kendisi üretmiyor?
- `docs/progress.md` ile `CLAUDE.md` çelişirse hangisi kazanır? Neden?
- Bir invariant'ı bozman gerekseydi ne yapardın?

---

## Bittiğinde

Bu on modülü bitirdiğinde, Sprint 1'in çoğunu kendin yazabilecek durumda olacaksın —
özellikle `data/cards.json`, bütçe testi ve kart bileşeni gibi izole parçaları.

Sonraki adım oku değil, yaz: küçük bir özellik seç, plan mode'da planını yaptır, ama
**kodu kendin yaz.** Takıldığında sor. Bu noktadan sonra ilerleme okuyarak değil,
yazarak geliyor.
