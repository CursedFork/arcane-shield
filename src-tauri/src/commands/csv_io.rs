use rusqlite::params;
use tauri::State;
use crate::DbState;

#[derive(serde::Serialize)]
pub struct CsvImportReport {
    pub inserted: usize,
    pub skipped: usize,
    pub errors: Vec<String>,
}

impl CsvImportReport {
    fn new() -> Self { Self { inserted: 0, skipped: 0, errors: vec![] } }
    fn skip(&mut self, msg: String) { self.errors.push(msg); self.skipped += 1; }
}

// ── Templates ────────────────────────────────────────────────────────────────

#[tauri::command]
pub fn csv_template(table: String) -> Result<String, String> {
    let hdr = match table.as_str() {
        "players"     => "player_name,character_name,ac,max_hp,initiative_mod,passive_perception,notes",
        "shops"       => "shop_name,item_name,price,quantity,notes",
        "party_items" => "item_name,owner,quantity,notes",
        "notes"       => "session_label,note_date,body",
        other => return Err(format!("unknown table: {other}")),
    };
    Ok(format!("{hdr}\r\n"))
}

// ── Export ───────────────────────────────────────────────────────────────────

#[tauri::command]
pub fn export_csv(state: State<DbState>, table: String) -> Result<String, String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    match table.as_str() {
        "players"     => export_players(&conn),
        "shops"       => export_shops(&conn),
        "party_items" => export_party_items(&conn),
        "notes"       => export_notes_csv(&conn),
        other => Err(format!("unknown table: {other}")),
    }
}

fn csv_string(f: impl FnOnce(&mut csv::Writer<Vec<u8>>) -> csv::Result<()>) -> Result<String, String> {
    let mut w = csv::Writer::from_writer(vec![]);
    f(&mut w).map_err(|e| e.to_string())?;
    String::from_utf8(w.into_inner().map_err(|e| e.to_string())?)
        .map_err(|e| e.to_string())
}

fn export_players(conn: &rusqlite::Connection) -> Result<String, String> {
    csv_string(|w| {
        w.write_record(["player_name","character_name","ac","max_hp","initiative_mod","passive_perception","notes"])?;
        let mut s = conn.prepare("SELECT player_name,character_name,ac,max_hp,initiative_mod,passive_perception,notes FROM players ORDER BY character_name").unwrap();
        let rows = s.query_map([], |r| Ok((
            r.get::<_,String>(0)?, r.get::<_,String>(1)?,
            r.get::<_,i64>(2)?,   r.get::<_,i64>(3)?,
            r.get::<_,i64>(4)?,   r.get::<_,i64>(5)?,
            r.get::<_,Option<String>>(6)?,
        ))).unwrap();
        for row in rows { let (pn,cn,ac,mhp,im,pp,nt) = row.unwrap(); w.write_record([&pn,&cn,&ac.to_string(),&mhp.to_string(),&im.to_string(),&pp.to_string(),&nt.unwrap_or_default()])?; }
        Ok(())
    })
}

fn export_shops(conn: &rusqlite::Connection) -> Result<String, String> {
    csv_string(|w| {
        w.write_record(["shop_name","item_name","price","quantity","notes"])?;
        let mut s = conn.prepare("SELECT shop_name,item_name,price,quantity,notes FROM shops ORDER BY shop_name,item_name").unwrap();
        let rows = s.query_map([], |r| Ok((
            r.get::<_,String>(0)?, r.get::<_,String>(1)?,
            r.get::<_,String>(2)?, r.get::<_,i64>(3)?,
            r.get::<_,Option<String>>(4)?,
        ))).unwrap();
        for row in rows { let (sn,it,pr,qt,nt) = row.unwrap(); w.write_record([&sn,&it,&pr,&qt.to_string(),&nt.unwrap_or_default()])?; }
        Ok(())
    })
}

fn export_party_items(conn: &rusqlite::Connection) -> Result<String, String> {
    csv_string(|w| {
        w.write_record(["item_name","owner","quantity","notes"])?;
        let mut s = conn.prepare("SELECT item_name,owner,quantity,notes FROM party_items ORDER BY owner,item_name").unwrap();
        let rows = s.query_map([], |r| Ok((
            r.get::<_,String>(0)?, r.get::<_,String>(1)?,
            r.get::<_,i64>(2)?,   r.get::<_,Option<String>>(3)?,
        ))).unwrap();
        for row in rows { let (it,ow,qt,nt) = row.unwrap(); w.write_record([&it,&ow,&qt.to_string(),&nt.unwrap_or_default()])?; }
        Ok(())
    })
}

fn export_notes_csv(conn: &rusqlite::Connection) -> Result<String, String> {
    csv_string(|w| {
        w.write_record(["session_label","note_date","body"])?;
        let mut s = conn.prepare("SELECT session_label,note_date,body FROM notes ORDER BY session_label DESC,note_date DESC").unwrap();
        let rows = s.query_map([], |r| Ok((
            r.get::<_,String>(0)?, r.get::<_,String>(1)?, r.get::<_,String>(2)?,
        ))).unwrap();
        for row in rows { let (sl,nd,bo) = row.unwrap(); w.write_record([&sl,&nd,&bo])?; }
        Ok(())
    })
}

// ── Import ───────────────────────────────────────────────────────────────────

#[tauri::command]
pub fn import_csv(state: State<DbState>, table: String, csv_text: String) -> Result<CsvImportReport, String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    match table.as_str() {
        "players"     => import_players(&conn, &csv_text),
        "shops"       => import_shops(&conn, &csv_text),
        "party_items" => import_party_items(&conn, &csv_text),
        "notes"       => import_notes(&conn, &csv_text),
        other => Err(format!("unknown table: {other}")),
    }
}

fn parse_i64(val: &str, field: &str, row: usize, r: &mut CsvImportReport) -> Option<i64> {
    match val.trim().parse::<i64>() {
        Ok(v) => Some(v),
        Err(_) => { r.skip(format!("row {row}: invalid integer for '{field}': '{val}'")); None }
    }
}

fn import_players(conn: &rusqlite::Connection, csv_text: &str) -> Result<CsvImportReport, String> {
    let mut rdr = csv::Reader::from_reader(csv_text.as_bytes());
    let mut r = CsvImportReport::new();
    for (i, res) in rdr.records().enumerate() {
        let rec = match res { Ok(x) => x, Err(e) => { r.skip(format!("row {}: {e}", i+2)); continue; } };
        if rec.len() < 6 { r.skip(format!("row {}: expected 6 columns, got {}", i+2, rec.len())); continue; }
        let pn = rec[0].trim().to_string();
        let cn = rec[1].trim().to_string();
        if pn.is_empty() || cn.is_empty() { r.skip(format!("row {}: player_name and character_name required", i+2)); continue; }
        let ac  = match parse_i64(rec[2].trim(), "ac",               i+2, &mut r) { Some(v)=>v, None=>continue };
        let mhp = match parse_i64(rec[3].trim(), "max_hp",           i+2, &mut r) { Some(v)=>v, None=>continue };
        let im  = match parse_i64(rec[4].trim(), "initiative_mod",   i+2, &mut r) { Some(v)=>v, None=>continue };
        let pp  = match parse_i64(rec[5].trim(), "passive_perception",i+2, &mut r) { Some(v)=>v, None=>continue };
        let nt: Option<String> = rec.get(6).map(|s| s.trim()).filter(|s| !s.is_empty()).map(String::from);
        match conn.execute("INSERT INTO players (player_name,character_name,ac,max_hp,initiative_mod,passive_perception,notes) VALUES (?1,?2,?3,?4,?5,?6,?7)",
            params![pn,cn,ac,mhp,im,pp,nt]) {
            Ok(_) => r.inserted += 1,
            Err(e) => r.skip(format!("row {}: db error: {e}", i+2)),
        }
    }
    Ok(r)
}

fn import_shops(conn: &rusqlite::Connection, csv_text: &str) -> Result<CsvImportReport, String> {
    let mut rdr = csv::Reader::from_reader(csv_text.as_bytes());
    let mut r = CsvImportReport::new();
    for (i, res) in rdr.records().enumerate() {
        let rec = match res { Ok(x) => x, Err(e) => { r.skip(format!("row {}: {e}", i+2)); continue; } };
        if rec.len() < 4 { r.skip(format!("row {}: expected 4 columns, got {}", i+2, rec.len())); continue; }
        let sn = rec[0].trim().to_string();
        let it = rec[1].trim().to_string();
        let pr = rec[2].trim().to_string();
        if sn.is_empty() || it.is_empty() { r.skip(format!("row {}: shop_name and item_name required", i+2)); continue; }
        let qt = match parse_i64(rec[3].trim(), "quantity", i+2, &mut r) { Some(v)=>v, None=>continue };
        if qt < 0 { r.skip(format!("row {}: quantity must be >= 0", i+2)); continue; }
        let nt: Option<String> = rec.get(4).map(|s| s.trim()).filter(|s| !s.is_empty()).map(String::from);
        match conn.execute("INSERT INTO shops (shop_name,item_name,price,quantity,notes) VALUES (?1,?2,?3,?4,?5)",
            params![sn,it,pr,qt,nt]) {
            Ok(_) => r.inserted += 1,
            Err(e) => r.skip(format!("row {}: db error: {e}", i+2)),
        }
    }
    Ok(r)
}

fn import_party_items(conn: &rusqlite::Connection, csv_text: &str) -> Result<CsvImportReport, String> {
    let mut rdr = csv::Reader::from_reader(csv_text.as_bytes());
    let mut r = CsvImportReport::new();
    for (i, res) in rdr.records().enumerate() {
        let rec = match res { Ok(x) => x, Err(e) => { r.skip(format!("row {}: {e}", i+2)); continue; } };
        if rec.len() < 3 { r.skip(format!("row {}: expected 3 columns, got {}", i+2, rec.len())); continue; }
        let it = rec[0].trim().to_string();
        let ow = rec[1].trim().to_string();
        if it.is_empty() || ow.is_empty() { r.skip(format!("row {}: item_name and owner required", i+2)); continue; }
        let qt = match parse_i64(rec[2].trim(), "quantity", i+2, &mut r) { Some(v)=>v, None=>continue };
        if qt < 0 { r.skip(format!("row {}: quantity must be >= 0", i+2)); continue; }
        let nt: Option<String> = rec.get(3).map(|s| s.trim()).filter(|s| !s.is_empty()).map(String::from);
        match conn.execute("INSERT INTO party_items (item_name,owner,quantity,notes) VALUES (?1,?2,?3,?4)",
            params![it,ow,qt,nt]) {
            Ok(_) => r.inserted += 1,
            Err(e) => r.skip(format!("row {}: db error: {e}", i+2)),
        }
    }
    Ok(r)
}

fn import_notes(conn: &rusqlite::Connection, csv_text: &str) -> Result<CsvImportReport, String> {
    let mut rdr = csv::Reader::from_reader(csv_text.as_bytes());
    let mut r = CsvImportReport::new();
    let now = chrono::Local::now().to_rfc3339();
    for (i, res) in rdr.records().enumerate() {
        let rec = match res { Ok(x) => x, Err(e) => { r.skip(format!("row {}: {e}", i+2)); continue; } };
        if rec.len() < 3 { r.skip(format!("row {}: expected 3 columns, got {}", i+2, rec.len())); continue; }
        let sl = rec[0].trim().to_string();
        let nd = rec[1].trim().to_string();
        let bo = rec[2].trim().to_string();
        if sl.is_empty() || nd.is_empty() || bo.is_empty() {
            r.skip(format!("row {}: session_label, note_date, and body are required", i+2));
            continue;
        }
        match conn.execute("INSERT INTO notes (session_label,note_date,body,created_at) VALUES (?1,?2,?3,?4)",
            params![sl,nd,bo,now]) {
            Ok(_) => r.inserted += 1,
            Err(e) => r.skip(format!("row {}: db error: {e}", i+2)),
        }
    }
    Ok(r)
}
