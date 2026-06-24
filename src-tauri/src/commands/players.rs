use rusqlite::params;
use tauri::State;
use crate::models::Player;
use crate::DbState;

#[tauri::command]
pub fn list_players(state: State<DbState>) -> Result<Vec<Player>, String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    let mut stmt = conn
        .prepare("SELECT id, player_name, character_name, ac, max_hp, initiative_mod, passive_perception, notes FROM players ORDER BY character_name")
        .map_err(|e| e.to_string())?;

    let rows = stmt.query_map([], |row| {
        Ok(Player {
            id: Some(row.get(0)?),
            player_name: row.get(1)?,
            character_name: row.get(2)?,
            ac: row.get(3)?,
            max_hp: row.get(4)?,
            initiative_mod: row.get(5)?,
            passive_perception: row.get(6)?,
            notes: row.get(7)?,
        })
    }).map_err(|e| e.to_string())?;

    rows.collect::<Result<Vec<_>, _>>().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_player(state: State<DbState>, id: i64) -> Result<Player, String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.query_row(
        "SELECT id, player_name, character_name, ac, max_hp, initiative_mod, passive_perception, notes FROM players WHERE id = ?1",
        params![id],
        |row| Ok(Player {
            id: Some(row.get(0)?),
            player_name: row.get(1)?,
            character_name: row.get(2)?,
            ac: row.get(3)?,
            max_hp: row.get(4)?,
            initiative_mod: row.get(5)?,
            passive_perception: row.get(6)?,
            notes: row.get(7)?,
        }),
    ).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn create_player(state: State<DbState>, player: Player) -> Result<i64, String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "INSERT INTO players (player_name, character_name, ac, max_hp, initiative_mod, passive_perception, notes)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
        params![
            player.player_name, player.character_name, player.ac,
            player.max_hp, player.initiative_mod, player.passive_perception, player.notes
        ],
    ).map_err(|e| e.to_string())?;
    Ok(conn.last_insert_rowid())
}

#[tauri::command]
pub fn update_player(state: State<DbState>, player: Player) -> Result<(), String> {
    let id = player.id.ok_or("player id required for update")?;
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "UPDATE players SET player_name=?1, character_name=?2, ac=?3, max_hp=?4,
         initiative_mod=?5, passive_perception=?6, notes=?7 WHERE id=?8",
        params![
            player.player_name, player.character_name, player.ac,
            player.max_hp, player.initiative_mod, player.passive_perception, player.notes, id
        ],
    ).map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
pub fn delete_player(state: State<DbState>, id: i64) -> Result<(), String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.execute("DELETE FROM players WHERE id=?1", params![id])
        .map_err(|e| e.to_string())?;
    Ok(())
}
