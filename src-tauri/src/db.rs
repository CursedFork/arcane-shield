use rusqlite::{Connection, Result};

pub fn run_migrations(conn: &Connection) -> Result<()> {
    conn.execute_batch("PRAGMA journal_mode=WAL;")?;
    conn.execute_batch("PRAGMA foreign_keys=ON;")?;

    conn.execute_batch("
        CREATE TABLE IF NOT EXISTS players (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name     TEXT NOT NULL,
            character_name  TEXT NOT NULL,
            ac              INTEGER NOT NULL,
            max_hp          INTEGER NOT NULL,
            initiative_mod  INTEGER NOT NULL,
            passive_perception INTEGER NOT NULL,
            notes           TEXT
        );

        CREATE TABLE IF NOT EXISTS magic_items (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            name                    TEXT NOT NULL,
            item_type               TEXT NOT NULL,
            rarity                  TEXT NOT NULL,
            requires_attunement     INTEGER NOT NULL DEFAULT 0,
            attunement_requirement  TEXT,
            description             TEXT NOT NULL,
            mechanical_effect       TEXT NOT NULL,
            charges                 INTEGER,
            source_campaign         TEXT,
            tags                    TEXT NOT NULL DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS bestiary (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            ac              INTEGER NOT NULL,
            max_hp          INTEGER NOT NULL,
            initiative_mod  INTEGER NOT NULL,
            cr              TEXT NOT NULL,
            statblock_md    TEXT NOT NULL,
            tags            TEXT NOT NULL DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS mechanics (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            body_md     TEXT NOT NULL,
            campaign    TEXT,
            tags        TEXT NOT NULL DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS campaigns (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            title   TEXT NOT NULL,
            body_md TEXT NOT NULL,
            tags    TEXT NOT NULL DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS notes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            session_label   TEXT NOT NULL,
            note_date       TEXT NOT NULL,
            body            TEXT NOT NULL,
            created_at      TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS shops (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_name   TEXT NOT NULL,
            item_name   TEXT NOT NULL,
            price       TEXT NOT NULL,
            quantity    INTEGER NOT NULL,
            notes       TEXT
        );

        CREATE TABLE IF NOT EXISTS party_items (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name   TEXT NOT NULL,
            owner       TEXT NOT NULL,
            quantity    INTEGER NOT NULL,
            notes       TEXT
        );

        CREATE TABLE IF NOT EXISTS saved_encounters (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            state_json  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        );
    ")?;

    Ok(())
}
