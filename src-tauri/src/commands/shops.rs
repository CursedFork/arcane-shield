use rusqlite::params;
use tauri::State;
use crate::models::ShopItem;
use crate::DbState;

fn row_to_shop_item(row: &rusqlite::Row) -> rusqlite::Result<ShopItem> {
    Ok(ShopItem {
        id: Some(row.get(0)?),
        shop_name: row.get(1)?,
        item_name: row.get(2)?,
        price: row.get(3)?,
        quantity: row.get(4)?,
        notes: row.get(5)?,
    })
}

#[tauri::command]
pub fn list_shop_items(state: State<DbState>) -> Result<Vec<ShopItem>, String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    let mut stmt = conn
        .prepare("SELECT id, shop_name, item_name, price, quantity, notes FROM shops ORDER BY shop_name, item_name")
        .map_err(|e| e.to_string())?;
    let rows = stmt.query_map([], row_to_shop_item).map_err(|e| e.to_string())?;
    rows.collect::<Result<Vec<_>, _>>().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn create_shop_item(state: State<DbState>, item: ShopItem) -> Result<i64, String> {
    if item.item_name.trim().is_empty() {
        return Err("item_name is required".into());
    }
    if item.quantity < 0 {
        return Err("quantity must be >= 0".into());
    }
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "INSERT INTO shops (shop_name, item_name, price, quantity, notes) VALUES (?1,?2,?3,?4,?5)",
        params![item.shop_name, item.item_name, item.price, item.quantity, item.notes],
    ).map_err(|e| e.to_string())?;
    Ok(conn.last_insert_rowid())
}

#[tauri::command]
pub fn update_shop_item(state: State<DbState>, item: ShopItem) -> Result<(), String> {
    let id = item.id.ok_or("id required for update")?;
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "UPDATE shops SET shop_name=?1, item_name=?2, price=?3, quantity=?4, notes=?5 WHERE id=?6",
        params![item.shop_name, item.item_name, item.price, item.quantity, item.notes, id],
    ).map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
pub fn delete_shop_item(state: State<DbState>, id: i64) -> Result<(), String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.execute("DELETE FROM shops WHERE id=?1", params![id])
        .map_err(|e| e.to_string())?;
    Ok(())
}
