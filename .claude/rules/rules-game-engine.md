<!-- TARGET PATH: .claude/rules/rules-game-engine.md -->
---
paths:
  - "src/kickcard/game/**/*.py"
  - "tests/game/**/*.py"
  - "data/cards.json"
---

# Duel engine rules

Bu dosya sadece engine dosyalarına dokunulduğunda yüklenir.

## Turn order — kesindir, değişmez

1. **Energy:** her iki oyuncu +2 (`ENERGY_PER_TURN`, 0'dan başlar, limit 10)
2. **Deploy:** aktif slot boşsa destedeki sıradaki kart, enerji yetiyorsa sahaya çıkar ve
   maliyeti düşülür. Yetmiyorsa slot boş kalır, enerji birikmeye devam eder.
3. **Combat:** eşzamanlı hasar. Tip avantajı **+10 flat** (çarpan değil), **sadece kart karta**.
4. **Overkill:** kartı öldüren hasarın fazlası core'a geçer.
5. **Cleanup:** `hp <= 0` olan kartlar çıkar; ölüm tetikleyicileri (`HANDOFF`, `SPAWN`,
   `REBIRTH`) burada çalışır.

Slotu boş olan tarafa karşı kart **tam hasarını doğrudan core'a** verir. Bu vuruşta tip bonusu
yoktur.

## Constants

```python
CORE_HP = 100
DECK_SIZE = 5
MAX_TURNS = 20
ENERGY_PER_TURN = 2
ENERGY_CAP = 10
TYPE_ADVANTAGE_BONUS = 10
```

Type triangle: `POWER > TRICK > AGILITY > POWER` (oyuncuya görünen: Güç > Hile > Çeviklik).
The type bonus applies only to card-vs-card hits, never to hits on an empty slot.

## Keywords

| Keyword | Effect | Budget cost |
|---|---|---|
| `FIRST_STRIKE` | Strikes first; if the opponent dies it cannot retaliate. If both sides have FIRST_STRIKE, damage is simultaneous | 35 |
| `ARMOR_X` (X = 5/10/15) | Reduces each hit on the card by X. Does not further reduce PIERCE's core portion or overkill | X + 10 |
| `PIERCE` | After the type bonus is added, half the damage (floored) goes straight to the core, the rest to the card | 15 |
| `OVERLOAD` | +20 damage on the card's first combat turn on the board, -10 afterwards (min 0). Also applies when hitting an empty slot | 20 |
| `HANDOFF` | On death, the owner's next deck card enters with +20 damage and +20 hp. Multiple HANDOFFs stack | 30 |
| `LINK` | +25 damage if the owner's previously deployed deck card has the same type. Tokens do not count | 20 |
| `PROTOCOL` | +10 damage for each other card of the same type in the owner's deck (not the board), max +40 | 20 |
| `SPAWN` | On death, a keywordless 25/25 token of its type enters the same slot. The next card waits until the token dies. The token's death triggers nothing | 15 |

Bir kartta **en fazla 1 keyword** olur. Death triggers (`HANDOFF`, `SPAWN`, `REBIRTH`) resolve in
Cleanup. `ECHO` and `RECYCLE` are out of v1 (backlog).

Synergy values (HANDOFF, LINK, PROTOCOL, SPAWN) are starting values. Once the card set exists they
are measured by simulation; if any deck wins more than 60% against the pool, values are lowered or
the total bonus on a card is capped.

## Signature abilities

- Legendary-only. A signature ability is a keyword marked "legendary only" in the keyword
  dictionary; it is that card's single keyword (at most 1 per card) and is priced by the budget
  formula like any other keyword.
- v1 has exactly one: `REBIRTH` (Diriliş), budget cost 15.

**`REBIRTH`:** the first time the card dies, it returns to the same slot with half of its current
max hp (floored to a multiple of 5, min 5). Damage bonuses are kept. The return is not a new
deploy; the slot stays occupied, so the next deck card waits. Overkill from the killing hit still
reaches the core. The second death is final.

## Hard requirements

- Engine is pure: no `random`, `datetime`, `asyncio`, DB or HTTP imports. Rastgelelik
  gerekirse çağıran taraf seed geçirir.
- Engine returns a `TurnLog` — overlay animasyonu bundan oynatılır. Yani engine
  **her turun tam durumunu** kaydeder, sadece kazananı değil.
- A draw is a real outcome, not an exception. 20. turda core'lar eşitse `DRAW`.
- The `TurnLog` carries a snapshot of every card's stats for that match. Later balance changes
  must not break old replays.

## Edge cases that must be tested

Yeni davranış eklerken bu listeyi genişlet.

- [ ] `test_mutual_kill_removes_both_cards`
- [ ] `test_overkill_damage_reaching_exactly_zero_ends_match`
- [ ] `test_first_strike_prevents_retaliation`
- [ ] `test_mutual_first_strike_resolves_simultaneously`
- [ ] `test_empty_slot_takes_full_damage_to_core`
- [ ] `test_expensive_opening_card_leaves_player_exposed`
- [ ] `test_pierce_and_overkill_do_not_double_count`
- [ ] `test_turn_limit_with_equal_cores_is_draw`
- [ ] `test_type_bonus_not_applied_to_empty_slot`
- [ ] `test_pierce_split_after_type_bonus`
- [ ] `test_armor_does_not_reduce_pierce_core_damage`
- [ ] `test_overload_bonus_only_on_first_combat_turn`
- [ ] `test_handoff_bonus_applies_to_next_deployed_card`
- [ ] `test_handoff_stacks`
- [ ] `test_link_ignores_tokens`
- [ ] `test_protocol_counts_deck_not_board`
- [ ] `test_spawn_token_blocks_next_deploy`
- [ ] `test_token_death_triggers_nothing`
- [ ] `test_rebirth_returns_once_with_half_max_hp`
- [ ] `test_rebirth_second_death_is_final`
- [ ] `test_rebirth_keeps_slot_blocked`
- [ ] `test_rebirth_overkill_still_reaches_core`

## Balance test

`tests/game/test_budget.py` iterates over every card in `data/cards.json` and asserts:

```
damage + hp + keyword_cost == cost * 25 + 10   (±5)
```

`keyword_cost` keyword sözlüğünden okunur; teste veya karta elle yazılmaz. Sözlüğün dosya yolu
bir sonraki adımda belirlenecek.

Bu test kırmızıysa **kartı düzelt, testi değil.** Formülü değiştirmek denge kararıdır,
kod kararı değil — önce sor.
