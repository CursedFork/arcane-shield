use rusqlite::params;
use tauri::State;
use crate::models::Note;
use crate::DbState;

fn row_to_note(row: &rusqlite::Row) -> rusqlite::Result<Note> {
    Ok(Note {
        id: Some(row.get(0)?),
        session_label: row.get(1)?,
        note_date: row.get(2)?,
        body: row.get(3)?,
        created_at: Some(row.get(4)?),
    })
}

#[tauri::command]
pub fn list_notes(state: State<DbState>) -> Result<Vec<Note>, String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    let mut stmt = conn
        .prepare("SELECT id, session_label, note_date, body, created_at FROM notes ORDER BY session_label DESC, note_date DESC")
        .map_err(|e| e.to_string())?;
    let rows = stmt.query_map([], row_to_note).map_err(|e| e.to_string())?;
    rows.collect::<Result<Vec<_>, _>>().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn create_note(state: State<DbState>, note: Note) -> Result<i64, String> {
    if note.body.trim().is_empty() {
        return Err("body is required".into());
    }
    let now = chrono::Local::now().to_rfc3339();
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "INSERT INTO notes (session_label, note_date, body, created_at) VALUES (?1,?2,?3,?4)",
        params![note.session_label, note.note_date, note.body, now],
    ).map_err(|e| e.to_string())?;
    Ok(conn.last_insert_rowid())
}

#[tauri::command]
pub fn update_note(state: State<DbState>, note: Note) -> Result<(), String> {
    let id = note.id.ok_or("id required for update")?;
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "UPDATE notes SET session_label=?1, note_date=?2, body=?3 WHERE id=?4",
        params![note.session_label, note.note_date, note.body, id],
    ).map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
pub fn delete_note(state: State<DbState>, id: i64) -> Result<(), String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.execute("DELETE FROM notes WHERE id=?1", params![id])
        .map_err(|e| e.to_string())?;
    Ok(())
}
