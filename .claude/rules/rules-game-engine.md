<!-- TARGET PATH: <project root>/.claude/rules/game-engine.md -->
---
paths:
  - "src/game/**/*.py"
  - "tests/game/**/*.py"
  - "data/cards.json"
---

# Duel engine rules

Bu dosya sadece engine dosyalarına dokunulduğunda yüklenir.

## Turn order — kesindir, değişmez

1. **Energy:** her iki oyuncu +1 (limit 10)
2. **Deploy:** aktif slot boşsa destedeki sıradaki kart, enerji yetiyorsa sahaya çıkar ve
   maliyeti düşülür. Yetmiyorsa slot boş kalır, enerji birikmeye devam eder.
3. **Combat:** eşzamanlı hasar. Tip avantajı **+10 flat** (çarpan değil).
4. **Overkill:** kartı öldüren hasarın fazlası core'a geçer.
5. **Cleanup:** `hp <= 0` olan kartlar çıkar, `ECHO` tetiklenir.

Slotu boş olan tarafa karşı kart **tam hasarını doğrudan core'a** verir.

## Constants

```python
CORE_HP = 30
DECK_SIZE = 5
MAX_TURNS = 20
ENERGY_CAP = 10
TYPE_ADVANTAGE_BONUS = 10
```

Type triangle: `HACK > CYBERDECK > WEAPON > HACK`

## Keywords

| Keyword | Effect | Budget cost |
|---|---|---|
| `FIRST_STRIKE` | Deals damage first; if the opponent dies it cannot retaliate | 25 |
| `ARMOR_X` | Reduces each incoming hit by X | X * 2 |
| `PIERCE` | Half its damage (floored) goes straight to the core | 20 |
| `ECHO` | On death, deals 15 to the opposing active card | 15 |
| `OVERLOAD` | +20 damage on its first turn, −10 afterwards | 10 |

Bir kartta **en fazla 1 keyword** olur.

## Hard requirements

- Engine is pure: no `random`, `datetime`, `asyncio`, DB or HTTP imports. Rastgelelik
  gerekirse çağıran taraf seed geçirir.
- Engine returns a `TurnLog` — overlay animasyonu bundan oynatılır. Yani engine
  **her turun tam durumunu** kaydeder, sadece kazananı değil.
- A draw is a real outcome, not an exception. 20. turda core'lar eşitse `DRAW`.

## Edge cases that must be tested

Yeni davranış eklerken bu listeyi genişlet.

- [ ] `test_mutual_kill_removes_both_cards`
- [ ] `test_overkill_damage_reaching_exactly_zero_ends_match`
- [ ] `test_first_strike_prevents_retaliation`
- [ ] `test_mutual_first_strike_resolves_simultaneously`
- [ ] `test_empty_slot_takes_full_damage_to_core`
- [ ] `test_expensive_opening_card_leaves_player_exposed`
- [ ] `test_pierce_and_overkill_do_not_double_count`
- [ ] `test_echo_kill_leaves_slot_empty_until_next_turn`
- [ ] `test_turn_limit_with_equal_cores_is_draw`

## Balance test

`tests/game/test_budget.py` iterates over every card in `data/cards.json` and asserts:

```
damage + hp + keyword_cost == cost * 25 + 10   (±5)
```

Bu test kırmızıysa **kartı düzelt, testi değil.** Formülü değiştirmek denge kararıdır,
kod kararı değil — önce sor.
