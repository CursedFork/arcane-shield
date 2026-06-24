use rusqlite::params;
use tauri::State;
use crate::models::MagicItem;
use crate::DbState;

const VALID_TYPES: &[&str] = &["Wondrous", "Weapon", "Armor", "Potion", "Ring", "Wand", "Staff", "Rod", "Scroll", "Other"];
const VALID_RARITIES: &[&str] = &["Common", "Uncommon", "Rare", "Very Rare", "Legendary", "Artifact"];

fn validate(item: &MagicItem) -> Result<(), String> {
    if item.name.trim().is_empty() {
        return Err("name is required".into());
    }
    if !VALID_TYPES.contains(&item.item_type.as_str()) {
        return Err(format!("item_type '{}' is not valid", item.item_type));
    }
    if !VALID_RARITIES.contains(&item.rarity.as_str()) {
        return Err(format!("rarity '{}' is not valid", item.rarity));
    }
    if let Some(c) = item.charges {
        if c < 0 {
            return Err("charges must be >= 0".into());
        }
    }
    Ok(())
}

fn row_to_item(row: &rusqlite::Row) -> rusqlite::Result<MagicItem> {
    let tags_str: String = row.get(10)?;
    let tags: Vec<String> = serde_json::from_str(&tags_str).unwrap_or_default();
    Ok(MagicItem {
        id: Some(row.get(0)?),
        name: row.get(1)?,
        item_type: row.get(2)?,
        rarity: row.get(3)?,
        requires_attunement: row.get::<_, i64>(4)? != 0,
        attunement_requirement: row.get(5)?,
        description: row.get(6)?,
        mechanical_effect: row.get(7)?,
        charges: row.get(8)?,
        source_campaign: row.get(9)?,
        tags,
    })
}

#[tauri::command]
pub fn list_items(state: State<DbState>) -> Result<Vec<MagicItem>, String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    let mut stmt = conn
        .prepare("SELECT id, name, item_type, rarity, requires_attunement, attunement_requirement, description, mechanical_effect, charges, source_campaign, tags FROM magic_items ORDER BY name")
        .map_err(|e| e.to_string())?;
    let rows = stmt.query_map([], row_to_item).map_err(|e| e.to_string())?;
    rows.collect::<Result<Vec<_>, _>>().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_item(state: State<DbState>, id: i64) -> Result<MagicItem, String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.query_row(
        "SELECT id, name, item_type, rarity, requires_attunement, attunement_requirement, description, mechanical_effect, charges, source_campaign, tags FROM magic_items WHERE id=?1",
        params![id],
        row_to_item,
    ).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn create_item(state: State<DbState>, item: MagicItem) -> Result<i64, String> {
    validate(&item)?;
    let tags = serde_json::to_string(&item.tags).map_err(|e| e.to_string())?;
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "INSERT INTO magic_items (name, item_type, rarity, requires_attunement, attunement_requirement, description, mechanical_effect, charges, source_campaign, tags)
         VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10)",
        params![
            item.name, item.item_type, item.rarity,
            item.requires_attunement as i64, item.attunement_requirement,
            item.description, item.mechanical_effect, item.charges,
            item.source_campaign, tags
        ],
    ).map_err(|e| e.to_string())?;
    Ok(conn.last_insert_rowid())
}

#[tauri::command]
pub fn update_item(state: State<DbState>, item: MagicItem) -> Result<(), String> {
    validate(&item)?;
    let id = item.id.ok_or("item id required for update")?;
    let tags = serde_json::to_string(&item.tags).map_err(|e| e.to_string())?;
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "UPDATE magic_items SET name=?1, item_type=?2, rarity=?3, requires_attunement=?4,
         attunement_requirement=?5, description=?6, mechanical_effect=?7, charges=?8,
         source_campaign=?9, tags=?10 WHERE id=?11",
        params![
            item.name, item.item_type, item.rarity,
            item.requires_attunement as i64, item.attunement_requirement,
            item.description, item.mechanical_effect, item.charges,
            item.source_campaign, tags, id
        ],
    ).map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
pub fn delete_item(state: State<DbState>, id: i64) -> Result<(), String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    conn.execute("DELETE FROM magic_items WHERE id=?1", params![id])
        .map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
pub fn search_items(
    state: State<DbState>,
    query: String,
    item_type: Option<String>,
    rarity: Option<String>,
    tags: Vec<String>,
    sort_by: String,
) -> Result<Vec<MagicItem>, String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    let pattern = format!("%{}%", query);

    let mut stmt = conn.prepare(
        "SELECT id, name, item_type, rarity, requires_attunement, attunement_requirement,
                description, mechanical_effect, charges, source_campaign, tags
         FROM magic_items WHERE name LIKE ?1",
    ).map_err(|e| e.to_string())?;

    let mut items: Vec<MagicItem> = stmt
        .query_map([&pattern], row_to_item)
        .map_err(|e| e.to_string())?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| e.to_string())?;

    if let Some(t) = item_type {
        if !t.is_empty() { items.retain(|i| i.item_type == t); }
    }
    if let Some(r) = rarity {
        if !r.is_empty() { items.retain(|i| i.rarity == r); }
    }
    if !tags.is_empty() {
        items.retain(|i| tags.iter().all(|t| i.tags.contains(t)));
    }

    match sort_by.as_str() {
        "rarity"    => items.sort_by(|a, b| a.rarity.cmp(&b.rarity).then(a.name.cmp(&b.name))),
        "item_type" => items.sort_by(|a, b| a.item_type.cmp(&b.item_type).then(a.name.cmp(&b.name))),
        _           => items.sort_by(|a, b| a.name.cmp(&b.name)),
    }

    Ok(items)
}
