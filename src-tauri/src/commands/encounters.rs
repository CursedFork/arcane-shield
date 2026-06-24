use rusqlite::params;
use tauri::State;
use crate::models::SavedEncounter;
use crate::DbState;

#[tauri::command]
pub fn list_saved_encounters(state: State<DbState>) -> Result<Vec<SavedEncounter>, String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    let mut stmt = conn
        .prepare("SELECT id, name, state_json, updated_at FROM saved_encounters ORDER BY updated_at DESC")
        .map_err(|e| e.to_string())?;
    let rows = stmt.query_map([], |row| {
        Ok(SavedEncounter {
            id: Some(row.get(0)?),
            name: row.get(1)?,
            state_json: row.get(2)?,
            updated_at: Some(row.get(3)?),
        })
    }).map_err(|e| e.to_string())?;
    rows.collect::<Result<Vec<_>, _>>().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn save_encounter(state: State<DbState>, encounter: SavedEncounter) -> Result<i64, String> {
    let now = chrono::Local::now().to_rfc3339();
    let conn = state.0.lock().map_err(|e| e.to_string())?;

    if let Some(id) = encounter.id {
        conn.execute(
            "UPDATE saved_encounters SET name=?1, state_json=?2, updated_at=?3 WHERE id=?4",
            params![encounter.name, encounter.state_json, now, id],
        ).map_err(|e| e.to_string())?;
        Ok(id)
    } else {
        conn.execute(
            "INSERT INTO saved_encounters (name, state_json, updated_at) VALUES (?1,?2,?3)",
            params![encounter.name, encounter.state_json, now],
        ).map_err(|e| e.to_string())?;
        Ok(conn.last_insert_rowid())
    }
}

#[tauri::command]
pub fn delete_saved_encounter(state: State<DbState>, id: i64) -> Result<(), String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.execute("DELETE FROM saved_encounters WHERE id=?1", params![id])
        .map_err(|e| e.to_string())?;
    Ok(())
}
