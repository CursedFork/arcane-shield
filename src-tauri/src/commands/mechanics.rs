use rusqlite::params;
use tauri::State;
use crate::models::Mechanic;
use crate::DbState;

fn row_to_mechanic(row: &rusqlite::Row) -> rusqlite::Result<Mechanic> {
    let tags_str: String = row.get(4)?;
    Ok(Mechanic {
        id: Some(row.get(0)?),
        title: row.get(1)?,
        body_md: row.get(2)?,
        campaign: row.get(3)?,
        tags: serde_json::from_str(&tags_str).unwrap_or_default(),
    })
}

#[tauri::command]
pub fn list_mechanics(state: State<DbState>) -> Result<Vec<Mechanic>, String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    let mut stmt = conn
        .prepare("SELECT id, title, body_md, campaign, tags FROM mechanics ORDER BY title")
        .map_err(|e| e.to_string())?;
    let rows = stmt.query_map([], row_to_mechanic).map_err(|e| e.to_string())?;
    rows.collect::<Result<Vec<_>, _>>().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_mechanic(state: State<DbState>, id: i64) -> Result<Mechanic, String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.query_row(
        "SELECT id, title, body_md, campaign, tags FROM mechanics WHERE id=?1",
        params![id],
        row_to_mechanic,
    ).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn create_mechanic(state: State<DbState>, mechanic: Mechanic) -> Result<i64, String> {
    if mechanic.title.trim().is_empty() {
        return Err("title is required".into());
    }
    let tags = serde_json::to_string(&mechanic.tags).map_err(|e| e.to_string())?;
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "INSERT INTO mechanics (title, body_md, campaign, tags) VALUES (?1,?2,?3,?4)",
        params![mechanic.title, mechanic.body_md, mechanic.campaign, tags],
    ).map_err(|e| e.to_string())?;
    Ok(conn.last_insert_rowid())
}

#[tauri::command]
pub fn update_mechanic(state: State<DbState>, mechanic: Mechanic) -> Result<(), String> {
    let id = mechanic.id.ok_or("id required for update")?;
    let tags = serde_json::to_string(&mechanic.tags).map_err(|e| e.to_string())?;
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "UPDATE mechanics SET title=?1, body_md=?2, campaign=?3, tags=?4 WHERE id=?5",
        params![mechanic.title, mechanic.body_md, mechanic.campaign, tags, id],
    ).map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
pub fn delete_mechanic(state: State<DbState>, id: i64) -> Result<(), String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.execute("DELETE FROM mechanics WHERE id=?1", params![id])
        .map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
pub fn search_mechanics(
    state: State<DbState>,
    query: String,
    campaign: Option<String>,
    tags: Vec<String>,
) -> Result<Vec<Mechanic>, String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    let pattern = format!("%{}%", query);

    let mut stmt = conn.prepare(
        "SELECT id, title, body_md, campaign, tags FROM mechanics WHERE title LIKE ?1 ORDER BY title",
    ).map_err(|e| e.to_string())?;

    let mut records: Vec<Mechanic> = stmt
        .query_map([&pattern], row_to_mechanic)
        .map_err(|e| e.to_string())?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| e.to_string())?;

    if let Some(c) = campaign {
        if !c.is_empty() { records.retain(|m| m.campaign.as_deref() == Some(&c)); }
    }
    if !tags.is_empty() {
        records.retain(|m| tags.iter().all(|t| m.tags.contains(t)));
    }

    Ok(records)
}
