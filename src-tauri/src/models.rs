use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct Player {
    pub id: Option<i64>,
    pub player_name: String,
    pub character_name: String,
    pub ac: i64,
    pub max_hp: i64,
    pub initiative_mod: i64,
    pub passive_perception: i64,
    pub notes: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct MagicItem {
    pub id: Option<i64>,
    pub name: String,
    pub item_type: String,
    pub rarity: String,
    pub requires_attunement: bool,
    pub attunement_requirement: Option<String>,
    pub description: String,
    pub mechanical_effect: String,
    pub charges: Option<i64>,
    pub source_campaign: Option<String>,
    pub tags: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct BestiaryEntry {
    pub id: Option<i64>,
    pub name: String,
    pub ac: i64,
    pub max_hp: i64,
    pub initiative_mod: i64,
    pub cr: String,
    pub statblock_md: String,
    pub tags: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct Mechanic {
    pub id: Option<i64>,
    pub title: String,
    pub body_md: String,
    pub campaign: Option<String>,
    pub tags: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct Campaign {
    pub id: Option<i64>,
    pub title: String,
    pub body_md: String,
    pub tags: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct Note {
    pub id: Option<i64>,
    pub session_label: String,
    pub note_date: String,
    pub body: String,
    pub created_at: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct ShopItem {
    pub id: Option<i64>,
    pub shop_name: String,
    pub item_name: String,
    pub price: String,
    pub quantity: i64,
    pub notes: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct PartyItem {
    pub id: Option<i64>,
    pub item_name: String,
    pub owner: String,
    pub quantity: i64,
    pub notes: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct SavedEncounter {
    pub id: Option<i64>,
    pub name: String,
    pub state_json: String,
    pub updated_at: Option<String>,
}

// Ephemeral — used in app state only (also serialized into saved_encounters.state_json)
#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct Combatant {
    pub id: String,
    pub source: String, // "player" | "monster" | "custom"
    pub display_name: String,
    pub ac: i64,
    pub current_hp: i64,
    pub max_hp: i64,
    pub initiative_roll: i64,
    pub conditions: Vec<String>,
    pub is_current_turn: bool,
}
