<!-- TARGET PATH: <project root>/.claude/rules/bot-overlay.md -->
---
paths:
  - "src/kickcard/bot/**/*.py"
  - "src/kickcard/ingest/**/*.py"
  - "src/kickcard/api/**/*.py"
  - "overlay/**"
---

# Bot and overlay rules

## Chat hygiene — en kritik kısım

Chat'i bot mesajlarıyla doldurmak bu projenin en büyük başarısızlık riski.

- **Silent on success.** Komut başarıyla işlendiyse chat'e hiçbir şey yazma. Geri bildirim
  overlay'de zaten var. Bot yalnızca **hata** durumunda tek satır yazar.
- **Batched summary.** 60 saniyede bir tek satır: "Son 1 dk: 14 paket, 2 legendary, 3 düello."
- **Only rare events reach chat.** Legendary pull ve düello galibiyeti evet;
  sıradan paket açma hayır.
- **Every bot message starts with the `⚡` prefix.** İzleyicilerin üçüncü parti chat
  client'larında filtreleyebilmesi için sabit kalmalı.
- **Global throttle:** max 5 commands processed per second. Aşan istekler reddedilmez,
  kuyruğa girer.
- **Auto slowdown:** chat hızı 15 msg/sn üzerine çıkarsa sistem `BUSY` moduna geçer;
  yalnızca read-only komutlar çalışır.

## Stream modes

Single Redis key. Bot and overlay both subscribe to it.

| Mode | Overlay | Bot replies | Eddies | `!paket` | `!düello` |
|---|---|---|---|---|---|
| `GAME` | full | normal | on | opens | on |
| `SILENT` | **draws nothing** | off | on | **goes to vault** | off |
| `BUSY` | full | reduced | on | queued | off |
| `OFF` | none | off | off | off | off |

Default and fail-safe mode is OFF — missing key, unrecognized value or Redis failure all resolve
to OFF.

`SILENT` mode RP yayınları için. Satın alınan paket **açılmadan vault'a** eklenir, bir sonraki
`GAME` yayınında `!kasa` ile toplu açılır. Bu modda satın alma onayları biriktirilir ve
bir sonraki `GAME` yayınının başında toplu olarak chat'e yazılır.

Mode changes fade out, they don't cut — ekrandan bir şeyin bir anda kaybolması da dikkat çekiyor.

## Input tolerance

Card references must resolve three ways: code (`cyp`), full name (`cyberpsycho`),
misspelling (Levenshtein <= 2). Belirsiz eşleşmede **sessizce tahmin etme** — seçenekleri yaz.

Chat komutları ve bot cevapları Türkçe kalır (izleyiciye görünür), ama komutları çözen
kodun isimlendirmesi İngilizce: `CommandRouter`, `resolve_card_reference()`, `CooldownStore`.

## Overlay

- The overlay is a **presentation layer**: it holds no state and makes no decisions. It replays
  the `TurnLog` it receives from the server. Oyun mantığını JS'e taşıma.
- One scene at a time. Redis queue; duels always preempt pack openings.
- If the queue exceeds 10, new `!paket` requests are rejected.
- Fully transparent when idle — no visible DOM elements left behind.
- Cards have **no illustrations** — typographic data files. One HTML template plus a
  rarity-based CSS class.

## Ingest

`src/ingest/` abstracts the Kick connection. Şu an resmi olmayan Pusher WS kullanılıyor,
ileride resmi webhook API'ına geçilecek. **This migration must be a single-file change** —
never leak Kick-specific types past the ingest boundary; convert to a `ChatMessage` object.

Message loss during an outage is permanent — no buffering, no replay. Downstream consumers
(activity tracking, eddie earning) must tolerate gaps rather than assume every message was seen.
