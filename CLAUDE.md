<!-- TARGET PATH: <project root>/CLAUDE.md -->
<!-- Bu HTML yorumları context'e yüklenmez, sadece sen görürsün. -->

# Kick Card Game

Kick yayınında çalışan chat kart oyunu. İzleyiciler sadakat puanıyla paket açar, kart toplar,
otomatik düello yapar. Sonuçlar OBS overlay'inde gösterilir.

Tam şartname: `docs/plan.md` — **stat, formül veya ekonomi rakamı gerektiğinde oku.**
Görev listesi: `docs/progress.md` — bir madde bitince kutuyu işaretle.

## Language policy

**Kod tamamen İngilizce. Bu kural istisnasızdır.**

| İngilizce (zorunlu) | Türkçe (izinli) |
|---|---|
| Dosya ve klasör isimleri | Bu dosyadaki ve `docs/` altındaki açıklama metinleri |
| Fonksiyon, sınıf, değişken, sabit isimleri | Chat komutları (`!paket`, `!deste`) — izleyiciye görünür |
| Veritabanı tablo ve kolon isimleri | Bot'un chat'e yazdığı mesajlar |
| JSON alan adları, enum değerleri | Kart isimleri ve lore metni |
| Kod içi yorumlar, docstring'ler, commit mesajları | Overlay'de görünen etiketler |
| Test isimleri (`test_first_strike_prevents_retaliation`) | |

Ayrım şu: **kod okuyanın gördüğü her şey İngilizce, izleyicinin gördüğü her şey Türkçe.**
Türkçe bir identifier görürsen düzelt, sorma. Türkçe karakter (ç, ğ, ı, ö, ş, ü) hiçbir
dosya adında, fonksiyon adında veya kolon adında geçmez.

## Commands

```bash
uv run pytest              # pytest, engine tests included
uv run ruff check .        # lint
uv run mypy src            # type check, strict on kickcard.game / kickcard.economy
```

Dev server ve db-reset komutları henüz yok — bkz. `docs/progress.md` Sprint 0.

Commit öncesi `uv run pytest`, `uv run ruff check .` ve `uv run mypy src` geçmeli.

## Architecture

```
src/
  kickcard/
    ingest/     Kick chat connection; raw message -> ChatMessage object
    bot/        command routing, cooldowns, chat replies
    game/       duel engine — PURE, no external dependencies
    economy/    eddies, pack opening, dust, pity
    store/      Postgres + Redis access
    api/        FastAPI, overlay WebSocket
overlay/      single-page HTML/CSS/JS, OBS browser source
data/         cards.json — single source of truth
tests/
```

## Invariants

Bunlar ihlal edilirse oyun sessizce bozulur. Bir tanesini bozman gerekiyorsa **önce sor.**

1. **`src/kickcard/game/` stays pure.** No DB, Redis, HTTP, clock or randomness. The duel engine is a
   deterministic function `(deck_a, deck_b) -> TurnLog`. Same input, same output, always.
2. **Card stats are never hand-written.** Every card satisfies
   `damage + hp + keyword_cost == cost * 25 + 10` (±5). `make test` enforces this. Test kırmızıysa
   kartı düzelt, testi değil.
3. **All balance changes go through `kickcard/economy/ledger.py`.** Every change writes a `ledger_entry`
   row with a non-empty reason. Never assign to `player.eddies` anywhere else.
4. **Card data lives in `data/cards.json`.** Never hardcode stats. The engine loads from there.
5. **Only `src/kickcard/bot/` writes to Kick.** Other layers emit events; they do not send chat messages.

## Do not

- Yeni bağımlılık ekleme — önce sor.
- Var olan testleri "geçsin diye" gevşetme. Test kırmızıysa kod yanlıştır.
- `data/cards.json` içindeki mevcut kartların statlarını denge tartışması olmadan değiştirme.
- Yorum yazarken kodun ne yaptığını tekrarlama; sadece **neden** öyle olduğunu yaz.
- Bir sprint'te olmayan özelliği "hazır başlamışken" ekleme.

## Conventions

- Type hints zorunlu. `mypy --strict` `src/kickcard/game/` ve `src/kickcard/economy/` üzerinde geçmeli.
- Dosya adları `snake_case.py`, sınıflar `PascalCase`, sabitler `UPPER_SNAKE`.
- Her yeni engine davranışı için önce test yaz, sonra kodu.
- Commit mesajları İngilizce, imperative mood: `add pity counter to pack opener`.
