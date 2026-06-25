mod db;
mod models;
mod commands;

use std::sync::Mutex;
use rusqlite::Connection;
use tauri::Manager;

use commands::{
    players::*,
    items::{list_items, get_item, create_item, update_item, delete_item, search_items},
    bestiary::{list_bestiary, get_bestiary_entry, create_bestiary_entry, update_bestiary_entry, delete_bestiary_entry, search_bestiary},
    mechanics::{list_mechanics, get_mechanic, create_mechanic, update_mechanic, delete_mechanic, search_mechanics},
    campaigns::{list_campaigns, get_campaign, create_campaign, update_campaign, delete_campaign, search_campaigns},
    notes::*,
    shops::*,
    party_items::*,
    encounters::*,
    import::*,
    csv_io::*,
    dice::roll,
};

pub struct DbState(pub Mutex<Connection>);

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .setup(|app| {
            let app_data_dir = app.path().app_data_dir()
                .expect("could not resolve app data directory");
            std::fs::create_dir_all(&app_data_dir)
                .expect("could not create app data directory");

            let db_path = app_data_dir.join("arcane-shield.db");
            let conn = Connection::open(&db_path)
                .expect("could not open SQLite database");
            db::run_migrations(&conn)
                .expect("database migration failed");

            app.manage(DbState(Mutex::new(conn)));
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            // Players
            list_players, get_player, create_player, update_player, delete_player,
            // Magic items
            list_items, get_item, create_item, update_item, delete_item, search_items,
            // Bestiary
            list_bestiary, get_bestiary_entry, create_bestiary_entry, update_bestiary_entry, delete_bestiary_entry, search_bestiary,
            // Mechanics
            list_mechanics, get_mechanic, create_mechanic, update_mechanic, delete_mechanic, search_mechanics,
            // Campaigns
            list_campaigns, get_campaign, create_campaign, update_campaign, delete_campaign, search_campaigns,
            // Notes
            list_notes, create_note, update_note, delete_note,
            // Shops
            list_shop_items, create_shop_item, update_shop_item, delete_shop_item,
            // Party items
            list_party_items, create_party_item, update_party_item, delete_party_item,
            // Encounters
            list_saved_encounters, save_encounter, delete_saved_encounter,
            // Import
            import_json,
            // CSV
            csv_template, export_csv, import_csv, import_paths,
            // Dice
            roll,
        ])
        .run(tauri::generate_context!())
        .expect("error while running Arcane Shield");
}
