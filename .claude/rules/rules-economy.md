<!-- TARGET PATH: <project root>/.claude/rules/economy.md -->
---
paths:
  - "src/kickcard/economy/**/*.py"
  - "tests/economy/**/*.py"
---

# Economy rules

`eddies` = kanalın sadakat puanı. v1'de tek para birimi, harcanabilir.
İkinci eksen (XP) **yok** — eklemeyi önerme.

## Earning

| Source | Amount |
|---|---|
| Activity | 10 per 5 min (must have chatted in the last 10 min) |
| Follow | 100, one-time |
| Subscription | 300 per month |
| Gifted sub | 150, to the gifter |
| Kicks tip | 1 eddie per Kick |
| **Per-stream activity cap** | **500** |

Gerekçe: yayınlar tipik olarak 4.5-5 saat sürüyor (54-60 tick); 400 tavanı 3s20'de doluyor ve en
sadık izleyiciyi son 1-1.5 saat ödülsüz bırakıyordu. 500 = 4s10, tavan hâlâ devrede ama artık denge
aracı değil farm koruması olarak çalışıyor.

## Packs

Price 100 eddies, 5 cards. Slot structure is fixed:

| Slot | Distribution |
|---|---|
| 1–3 | common |
| 4 | uncommon 85% / rare 15% |
| 5 | rare 80% / epic 18% / legendary 2% |

**Pity:** 30 pakette legendary çıkmadıysa 30. pakette garanti, sayaç sıfırlanır.
`player.pity_counter` **paket açılışıyla aynı transaction'da** güncellenir.

## Dust

| Rarity | Yield | Craft cost |
|---|---|---|
| common | 5 | 20 |
| uncommon | 15 | 60 |
| rare | 50 | 200 |
| epic | 150 | 600 |
| legendary | 500 | 2000 |

Deste 5 tekil karttan oluştuğu için ikinci kopya işe yaramaz → duplicates auto-convert to dust.
Starter deck cards **cannot be dusted.**

## Hard requirements

- **Every balance change goes through `ledger.py` and writes a `ledger_entry`.** The `reason`
  field is never empty. Ekonomi bozulduğunda tek teşhis aracı bu tablo.
- **Pack opening is atomic.** Balance debit, card grant, pity counter and dust conversion in a
  single transaction. Yarım kalırsa tamamı geri alınır.
- **Randomness is injected.** `PackOpener(rng)` — never call `random` at module level.
  Tests run with a fixed seed.
- **Negative balances are impossible.** The debit path checks the balance and raises
  `InsufficientBalanceError`. Kontrolü çağıran tarafa bırakma.
- Yeni bir eddie kaynağı veya harcama kalemi ekleme — bunlar ekonomi kararı, önce sor.

## Health check

Ortalama aktif izleyici yayın başına ~400 eddie = 4 pack = 20 card kazanmalı.
Bu oran değişirse koleksiyon tamamlama süresi bozulur.

`tests/economy/test_simulation.py` simulates 1000 virtual players over 5 streams and asserts
that average collection completion lands between 4 and 6 streams.
