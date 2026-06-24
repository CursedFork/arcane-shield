use rusqlite::params;
use tauri::State;
use crate::models::PartyItem;
use crate::DbState;

fn row_to_party_item(row: &rusqlite::Row) -> rusqlite::Result<PartyItem> {
    Ok(PartyItem {
        id: Some(row.get(0)?),
        item_name: row.get(1)?,
        owner: row.get(2)?,
        quantity: row.get(3)?,
        notes: row.get(4)?,
    })
}

#[tauri::command]
pub fn list_party_items(state: State<DbState>) -> Result<Vec<PartyItem>, String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    let mut stmt = conn
        .prepare("SELECT id, item_name, owner, quantity, notes FROM party_items ORDER BY owner, item_name")
        .map_err(|e| e.to_string())?;
    let rows = stmt.query_map([], row_to_party_item).map_err(|e| e.to_string())?;
    rows.collect::<Result<Vec<_>, _>>().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn create_party_item(state: State<DbState>, item: PartyItem) -> Result<i64, String> {
    if item.item_name.trim().is_empty() {
        return Err("item_name is required".into());
    }
    if item.quantity < 0 {
        return Err("quantity must be >= 0".into());
    }
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "INSERT INTO party_items (item_name, owner, quantity, notes) VALUES (?1,?2,?3,?4)",
        params![item.item_name, item.owner, item.quantity, item.notes],
    ).map_err(|e| e.to_string())?;
    Ok(conn.last_insert_rowid())
}

#[tauri::command]
pub fn update_party_item(state: State<DbState>, item: PartyItem) -> Result<(), String> {
    let id = item.id.ok_or("id required for update")?;
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "UPDATE party_items SET item_name=?1, owner=?2, quantity=?3, notes=?4 WHERE id=?5",
        params![item.item_name, item.owner, item.quantity, item.notes, id],
    ).map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
pub fn delete_party_item(state: State<DbState>, id: i64) -> Result<(), String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.execute("DELETE FROM party_items WHERE id=?1", params![id])
        .map_err(|e| e.to_string())?;
    Ok(())
}
