use rusqlite::params;
use tauri::State;
use crate::models::BestiaryEntry;
use crate::DbState;

fn row_to_entry(row: &rusqlite::Row) -> rusqlite::Result<BestiaryEntry> {
    let tags_str: String = row.get(7)?;
    let tags: Vec<String> = serde_json::from_str(&tags_str).unwrap_or_default();
    Ok(BestiaryEntry {
        id: Some(row.get(0)?),
        name: row.get(1)?,
        ac: row.get(2)?,
        max_hp: row.get(3)?,
        initiative_mod: row.get(4)?,
        cr: row.get(5)?,
        statblock_md: row.get(6)?,
        tags,
    })
}

#[tauri::command]
pub fn list_bestiary(state: State<DbState>) -> Result<Vec<BestiaryEntry>, String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    let mut stmt = conn
        .prepare("SELECT id, name, ac, max_hp, initiative_mod, cr, statblock_md, tags FROM bestiary ORDER BY name")
        .map_err(|e| e.to_string())?;
    let rows = stmt.query_map([], row_to_entry).map_err(|e| e.to_string())?;
    rows.collect::<Result<Vec<_>, _>>().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_bestiary_entry(state: State<DbState>, id: i64) -> Result<BestiaryEntry, String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.query_row(
        "SELECT id, name, ac, max_hp, initiative_mod, cr, statblock_md, tags FROM bestiary WHERE id=?1",
        params![id],
        row_to_entry,
    ).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn create_bestiary_entry(state: State<DbState>, entry: BestiaryEntry) -> Result<i64, String> {
    if entry.name.trim().is_empty() {
        return Err("name is required".into());
    }
    let tags = serde_json::to_string(&entry.tags).map_err(|e| e.to_string())?;
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "INSERT INTO bestiary (name, ac, max_hp, initiative_mod, cr, statblock_md, tags) VALUES (?1,?2,?3,?4,?5,?6,?7)",
        params![entry.name, entry.ac, entry.max_hp, entry.initiative_mod, entry.cr, entry.statblock_md, tags],
    ).map_err(|e| e.to_string())?;
    Ok(conn.last_insert_rowid())
}

#[tauri::command]
pub fn update_bestiary_entry(state: State<DbState>, entry: BestiaryEntry) -> Result<(), String> {
    let id = entry.id.ok_or("id required for update")?;
    let tags = serde_json::to_string(&entry.tags).map_err(|e| e.to_string())?;
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "UPDATE bestiary SET name=?1, ac=?2, max_hp=?3, initiative_mod=?4, cr=?5, statblock_md=?6, tags=?7 WHERE id=?8",
        params![entry.name, entry.ac, entry.max_hp, entry.initiative_mod, entry.cr, entry.statblock_md, tags, id],
    ).map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
pub fn delete_bestiary_entry(state: State<DbState>, id: i64) -> Result<(), String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.execute("DELETE FROM bestiary WHERE id=?1", params![id])
        .map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
pub fn search_bestiary(
    state: State<DbState>,
    query: String,
    cr: Option<String>,
    tags: Vec<String>,
    sort_by: String,
) -> Result<Vec<BestiaryEntry>, String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    let pattern = format!("%{}%", query);

    let mut stmt = conn.prepare(
        "SELECT id, name, ac, max_hp, initiative_mod, cr, statblock_md, tags
         FROM bestiary WHERE name LIKE ?1",
    ).map_err(|e| e.to_string())?;

    let mut entries: Vec<BestiaryEntry> = stmt
        .query_map([&pattern], row_to_entry)
        .map_err(|e| e.to_string())?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| e.to_string())?;

    if let Some(c) = cr {
        if !c.is_empty() { entries.retain(|e| e.cr == c); }
    }
    if !tags.is_empty() {
        entries.retain(|e| tags.iter().all(|t| e.tags.contains(t)));
    }

    match sort_by.as_str() {
        "cr"  => entries.sort_by(|a, b| cr_sort_key(&a.cr).cmp(&cr_sort_key(&b.cr)).then(a.name.cmp(&b.name))),
        "ac"  => entries.sort_by(|a, b| a.ac.cmp(&b.ac).then(a.name.cmp(&b.name))),
        _     => entries.sort_by(|a, b| a.name.cmp(&b.name)),
    }

    Ok(entries)
}

fn cr_sort_key(cr: &str) -> u32 {
    match cr {
        "0"    => 0,
        "1/8"  => 1,
        "1/4"  => 2,
        "1/2"  => 3,
        other  => other.parse::<u32>().unwrap_or(999).saturating_add(3),
    }
}
