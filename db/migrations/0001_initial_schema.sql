CREATE TABLE player (
    kick_user_id BIGINT PRIMARY KEY,
    username TEXT NOT NULL,
    eddies INTEGER NOT NULL DEFAULT 0
        CONSTRAINT player_eddies_non_negative_check CHECK (eddies >= 0),
    dust INTEGER NOT NULL DEFAULT 0
        CONSTRAINT player_dust_non_negative_check CHECK (dust >= 0),
    pity_counter INTEGER NOT NULL DEFAULT 0
        CONSTRAINT player_pity_counter_non_negative_check CHECK (pity_counter >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_active_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE collection (
    kick_user_id BIGINT NOT NULL REFERENCES player (kick_user_id),
    card_id TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0
        CONSTRAINT collection_quantity_non_negative_check CHECK (quantity >= 0),
    PRIMARY KEY (kick_user_id, card_id)
);

CREATE FUNCTION jsonb_array_has_unique_elements(arr JSONB) RETURNS BOOLEAN AS $$
    SELECT COUNT(DISTINCT value) = COUNT(*)
    FROM jsonb_array_elements_text(arr) AS t(value)
$$ LANGUAGE sql IMMUTABLE STRICT;

CREATE TABLE deck (
    kick_user_id BIGINT PRIMARY KEY REFERENCES player (kick_user_id),
    card_ids JSONB NOT NULL,
    CONSTRAINT deck_has_five_cards_check CHECK (jsonb_array_length(card_ids) = 5),
    CONSTRAINT deck_cards_are_unique_check CHECK (jsonb_array_has_unique_elements(card_ids))
);

CREATE TABLE duel (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    player_a BIGINT NOT NULL REFERENCES player (kick_user_id),
    player_b BIGINT NOT NULL REFERENCES player (kick_user_id),
    winner BIGINT REFERENCES player (kick_user_id),
    turn_log JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT duel_players_differ_check CHECK (player_a <> player_b),
    CONSTRAINT duel_winner_is_participant_check
        CHECK (winner IS NULL OR winner IN (player_a, player_b))
);

CREATE TABLE ledger_entry (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kick_user_id BIGINT NOT NULL REFERENCES player (kick_user_id),
    kind TEXT NOT NULL,
    currency TEXT NOT NULL
        CONSTRAINT ledger_entry_currency_is_valid_check CHECK (currency IN ('eddies', 'dust')),
    amount INTEGER NOT NULL
        CONSTRAINT ledger_entry_amount_is_nonzero_check CHECK (amount <> 0),
    reason TEXT NOT NULL
        CONSTRAINT ledger_entry_reason_is_not_empty_check CHECK (reason <> ''),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ledger_entry_kick_user_id_created_at_idx
    ON ledger_entry (kick_user_id, created_at);
