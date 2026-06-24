use std::path::PathBuf;
use rusqlite::params;
use tauri::State;
use crate::models::{MagicItem, BestiaryEntry, Mechanic, Campaign};
use crate::DbState;

#[derive(serde::Serialize)]
pub struct ImportReport {
    pub magic_items: ImportResult,
    pub bestiary: ImportResult,
    pub mechanics: ImportResult,
    pub campaigns: ImportResult,
}

#[derive(serde::Serialize)]
pub struct ImportResult {
    pub inserted: usize,
    pub skipped: usize,
    pub errors: Vec<String>,
}

impl ImportResult {
    fn new() -> Self {
        Self { inserted: 0, skipped: 0, errors: Vec::new() }
    }
}

/// Import all JSON files from the Phase 0 output directory into the DB.
/// Each file is optional — missing files are silently skipped.
#[tauri::command]
pub fn import_json(state: State<DbState>, json_dir: String) -> Result<ImportReport, String> {
    let dir = PathBuf::from(&json_dir);
    let conn = state.0.lock().map_err(|e| e.to_string())?;

    let magic_items  = import_magic_items(&conn, &dir);
    let bestiary     = import_bestiary(&conn, &dir);
    let mechanics    = import_mechanics(&conn, &dir);
    let campaigns    = import_campaigns(&conn, &dir);

    Ok(ImportReport { magic_items, bestiary, mechanics, campaigns })
}

fn read_json<T: serde::de::DeserializeOwned>(dir: &PathBuf, filename: &str) -> Option<Vec<T>> {
    let path = dir.join(filename);
    if !path.exists() {
        return None;
    }
    let text = std::fs::read_to_string(&path).ok()?;
    serde_json::from_str(&text).ok()
}

fn import_magic_items(conn: &rusqlite::Connection, dir: &PathBuf) -> ImportResult {
    let mut result = ImportResult::new();
    let Some(items) = read_json::<MagicItem>(dir, "magic_items.json") else {
        return result;
    };

    for item in items {
        if item.name.trim().is_empty() {
            result.errors.push("skipped: missing name".into());
            result.skipped += 1;
            continue;
        }
        let tags = match serde_json::to_string(&item.tags) {
            Ok(t) => t,
            Err(e) => { result.errors.push(format!("tags error for '{}': {}", item.name, e)); result.skipped += 1; continue; }
        };
        match conn.execute(
            "INSERT INTO magic_items (name, item_type, rarity, requires_attunement, attunement_requirement, description, mechanical_effect, charges, source_campaign, tags)
             VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10)",
            params![item.name, item.item_type, item.rarity, item.requires_attunement as i64,
                    item.attunement_requirement, item.description, item.mechanical_effect,
                    item.charges, item.source_campaign, tags],
        ) {
            Ok(_) => result.inserted += 1,
            Err(e) => { result.errors.push(format!("'{}': {}", item.name, e)); result.skipped += 1; }
        }
    }
    result
}

fn import_bestiary(conn: &rusqlite::Connection, dir: &PathBuf) -> ImportResult {
    let mut result = ImportResult::new();
    let Some(entries) = read_json::<BestiaryEntry>(dir, "bestiary.json") else {
        return result;
    };

    for entry in entries {
        if entry.name.trim().is_empty() {
            result.errors.push("skipped: missing name".into());
            result.skipped += 1;
            continue;
        }
        let tags = match serde_json::to_string(&entry.tags) {
            Ok(t) => t,
            Err(e) => { result.errors.push(format!("tags error for '{}': {}", entry.name, e)); result.skipped += 1; continue; }
        };
        match conn.execute(
            "INSERT INTO bestiary (name, ac, max_hp, initiative_mod, cr, statblock_md, tags) VALUES (?1,?2,?3,?4,?5,?6,?7)",
            params![entry.name, entry.ac, entry.max_hp, entry.initiative_mod, entry.cr, entry.statblock_md, tags],
        ) {
            Ok(_) => result.inserted += 1,
            Err(e) => { result.errors.push(format!("'{}': {}", entry.name, e)); result.skipped += 1; }
        }
    }
    result
}

fn import_mechanics(conn: &rusqlite::Connection, dir: &PathBuf) -> ImportResult {
    let mut result = ImportResult::new();
    let Some(records) = read_json::<Mechanic>(dir, "mechanics.json") else {
        return result;
    };

    for m in records {
        if m.title.trim().is_empty() {
            result.errors.push("skipped: missing title".into());
            result.skipped += 1;
            continue;
        }
        let tags = match serde_json::to_string(&m.tags) {
            Ok(t) => t,
            Err(e) => { result.errors.push(format!("tags error for '{}': {}", m.title, e)); result.skipped += 1; continue; }
        };
        match conn.execute(
            "INSERT INTO mechanics (title, body_md, campaign, tags) VALUES (?1,?2,?3,?4)",
            params![m.title, m.body_md, m.campaign, tags],
        ) {
            Ok(_) => result.inserted += 1,
            Err(e) => { result.errors.push(format!("'{}': {}", m.title, e)); result.skipped += 1; }
        }
    }
    result
}

fn import_campaigns(conn: &rusqlite::Connection, dir: &PathBuf) -> ImportResult {
    let mut result = ImportResult::new();
    let Some(records) = read_json::<Campaign>(dir, "campaigns.json") else {
        return result;
    };

    for c in records {
        if c.title.trim().is_empty() {
            result.errors.push("skipped: missing title".into());
            result.skipped += 1;
            continue;
        }
        let tags = match serde_json::to_string(&c.tags) {
            Ok(t) => t,
            Err(e) => { result.errors.push(format!("tags error for '{}': {}", c.title, e)); result.skipped += 1; continue; }
        };
        match conn.execute(
            "INSERT INTO campaigns (title, body_md, tags) VALUES (?1,?2,?3)",
            params![c.title, c.body_md, tags],
        ) {
            Ok(_) => result.inserted += 1,
            Err(e) => { result.errors.push(format!("'{}': {}", c.title, e)); result.skipped += 1; }
        }
    }
    result
}
