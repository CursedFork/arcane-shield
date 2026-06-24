use rusqlite::params;
use tauri::State;
use crate::models::Campaign;
use crate::DbState;

fn row_to_campaign(row: &rusqlite::Row) -> rusqlite::Result<Campaign> {
    let tags_str: String = row.get(3)?;
    Ok(Campaign {
        id: Some(row.get(0)?),
        title: row.get(1)?,
        body_md: row.get(2)?,
        tags: serde_json::from_str(&tags_str).unwrap_or_default(),
    })
}

#[tauri::command]
pub fn list_campaigns(state: State<DbState>) -> Result<Vec<Campaign>, String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    let mut stmt = conn
        .prepare("SELECT id, title, body_md, tags FROM campaigns ORDER BY title")
        .map_err(|e| e.to_string())?;
    let rows = stmt.query_map([], row_to_campaign).map_err(|e| e.to_string())?;
    rows.collect::<Result<Vec<_>, _>>().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_campaign(state: State<DbState>, id: i64) -> Result<Campaign, String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.query_row(
        "SELECT id, title, body_md, tags FROM campaigns WHERE id=?1",
        params![id],
        row_to_campaign,
    ).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn create_campaign(state: State<DbState>, campaign: Campaign) -> Result<i64, String> {
    if campaign.title.trim().is_empty() {
        return Err("title is required".into());
    }
    let tags = serde_json::to_string(&campaign.tags).map_err(|e| e.to_string())?;
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "INSERT INTO campaigns (title, body_md, tags) VALUES (?1,?2,?3)",
        params![campaign.title, campaign.body_md, tags],
    ).map_err(|e| e.to_string())?;
    Ok(conn.last_insert_rowid())
}

#[tauri::command]
pub fn update_campaign(state: State<DbState>, campaign: Campaign) -> Result<(), String> {
    let id = campaign.id.ok_or("id required for update")?;
    let tags = serde_json::to_string(&campaign.tags).map_err(|e| e.to_string())?;
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "UPDATE campaigns SET title=?1, body_md=?2, tags=?3 WHERE id=?4",
        params![campaign.title, campaign.body_md, tags, id],
    ).map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
pub fn delete_campaign(state: State<DbState>, id: i64) -> Result<(), String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.execute("DELETE FROM campaigns WHERE id=?1", params![id])
        .map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
pub fn search_campaigns(
    state: State<DbState>,
    query: String,
    tags: Vec<String>,
) -> Result<Vec<Campaign>, String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    let pattern = format!("%{}%", query);

    let mut stmt = conn.prepare(
        "SELECT id, title, body_md, tags FROM campaigns WHERE title LIKE ?1 ORDER BY title",
    ).map_err(|e| e.to_string())?;

    let mut records: Vec<Campaign> = stmt
        .query_map([&pattern], row_to_campaign)
        .map_err(|e| e.to_string())?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| e.to_string())?;

    if !tags.is_empty() {
        records.retain(|c| tags.iter().all(|t| c.tags.contains(t)));
    }

    Ok(records)
}
