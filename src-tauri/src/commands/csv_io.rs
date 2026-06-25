use rusqlite::params;
use serde::Serialize;
use tauri::State;
use crate::DbState;

// ── Report types ─────────────────────────────────────────────────────────────

#[derive(Serialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct CsvImportReport {
    pub inserted: usize,
    pub skipped: usize,
    pub errors: Vec<String>,
}

impl CsvImportReport {
    fn new() -> Self { Self { inserted: 0, skipped: 0, errors: vec![] } }
    fn skip(&mut self, msg: String) { self.errors.push(msg); self.skipped += 1; }
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct FileImportResult {
    pub path: String,
    pub filename: String,
    pub table: String,          // detected table name, or "unknown"
    pub status: String,         // "ok" | "unknown" | "error"
    pub inserted: usize,
    pub skipped_rows: usize,
    pub errors: Vec<String>,
}

// ── Tag helpers ───────────────────────────────────────────────────────────────

fn tags_from_csv(s: &str) -> Vec<String> {
    if s.trim().is_empty() { return vec![]; }
    s.split(';').map(|t| t.trim().to_string()).filter(|t| !t.is_empty()).collect()
}

fn tags_to_csv(json: &str) -> String {
    serde_json::from_str::<Vec<String>>(json).unwrap_or_default().join(";")
}

fn tags_to_json(tags: &[String]) -> String {
    serde_json::to_string(tags).unwrap_or_else(|_| "[]".into())
}

// ── Table detection ───────────────────────────────────────────────────────────

fn detect_table_by_headers(csv_text: &str) -> Option<&'static str> {
    let hdr = csv_text.lines().next()?.to_lowercase();
    // Most specific checks first
    if hdr.contains("player_name") && hdr.contains("character_name") { return Some("players"); }
    if hdr.contains("shop_name") && hdr.contains("item_name") { return Some("shops"); }
    if hdr.contains("item_name") && hdr.contains("owner") { return Some("party_items"); }
    if hdr.contains("session_label") && hdr.contains("note_date") { return Some("notes"); }
    if hdr.contains("item_type") && hdr.contains("rarity") { return Some("magic_items"); }
    if hdr.contains("statblock") || (hdr.contains("initiative_mod") && hdr.contains("cr")) { return Some("bestiary"); }
    if hdr.contains("body_md") && hdr.contains("campaign") { return Some("mechanics"); }
    if hdr.contains("body_md") { return Some("campaigns"); }
    None
}

fn detect_table_by_filename(filename: &str) -> Option<&'static str> {
    let n = filename.to_lowercase();
    if n.contains("player") || n.contains("roster") { return Some("players"); }
    if n.contains("party_item") || n.contains("party-item") || n.contains("partyitem") { return Some("party_items"); }
    if n.contains("magic") || n.contains("magic_item") { return Some("magic_items"); }
    if n.contains("bestiar") || n.contains("monster") { return Some("bestiary"); }
    if n.contains("mechanic") || n.contains("rule") { return Some("mechanics"); }
    if n.contains("campaign") || n.contains("world") { return Some("campaigns"); }
    if n.contains("note") || n.contains("session") { return Some("notes"); }
    if n.contains("shop") || n.contains("vendor") || n.contains("store") { return Some("shops"); }
    if n.contains("loot") || n.contains("party") { return Some("party_items"); }
    if n.contains("item") { return Some("magic_items"); }
    None
}

fn detect_table(filename: &str, csv_text: &str) -> Option<&'static str> {
    detect_table_by_headers(csv_text).or_else(|| detect_table_by_filename(filename))
}

// ── Templates ────────────────────────────────────────────────────────────────

#[tauri::command]
pub fn csv_template(table: String) -> Result<String, String> {
    let hdr = match table.as_str() {
        "players"     => "player_name,character_name,ac,max_hp,initiative_mod,passive_perception,notes",
        "shops"       => "shop_name,item_name,price,quantity,notes",
        "party_items" => "item_name,owner,quantity,notes",
        "notes"       => "session_label,note_date,body",
        "magic_items" => "name,item_type,rarity,requires_attunement,attunement_requirement,description,mechanical_effect,charges,source_campaign,tags",
        "bestiary"    => "name,ac,max_hp,initiative_mod,cr,statblock_md,tags",
        "mechanics"   => "title,body_md,campaign,tags",
        "campaigns"   => "title,body_md,tags",
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
        "magic_items" => export_magic_items(&conn),
        "bestiary"    => export_bestiary(&conn),
        "mechanics"   => export_mechanics(&conn),
        "campaigns"   => export_campaigns(&conn),
        other => Err(format!("unknown table: {other}")),
    }
}

fn csv_string(f: impl FnOnce(&mut csv::Writer<Vec<u8>>) -> csv::Result<()>) -> Result<String, String> {
    let mut w = csv::Writer::from_writer(vec![]);
    f(&mut w).map_err(|e| e.to_string())?;
    String::from_utf8(w.into_inner().map_err(|e| e.to_string())?).map_err(|e| e.to_string())
}

fn export_players(conn: &rusqlite::Connection) -> Result<String, String> {
    csv_string(|w| {
        w.write_record(["player_name","character_name","ac","max_hp","initiative_mod","passive_perception","notes"])?;
        let mut s = conn.prepare("SELECT player_name,character_name,ac,max_hp,initiative_mod,passive_perception,notes FROM players ORDER BY character_name").unwrap();
        let rows = s.query_map([], |r| Ok((r.get::<_,String>(0)?, r.get::<_,String>(1)?, r.get::<_,i64>(2)?, r.get::<_,i64>(3)?, r.get::<_,i64>(4)?, r.get::<_,i64>(5)?, r.get::<_,Option<String>>(6)?))).unwrap();
        for row in rows { let (pn,cn,ac,mhp,im,pp,nt) = row.unwrap(); w.write_record([&pn,&cn,&ac.to_string(),&mhp.to_string(),&im.to_string(),&pp.to_string(),&nt.unwrap_or_default()])?; }
        Ok(())
    })
}

fn export_shops(conn: &rusqlite::Connection) -> Result<String, String> {
    csv_string(|w| {
        w.write_record(["shop_name","item_name","price","quantity","notes"])?;
        let mut s = conn.prepare("SELECT shop_name,item_name,price,quantity,notes FROM shops ORDER BY shop_name,item_name").unwrap();
        let rows = s.query_map([], |r| Ok((r.get::<_,String>(0)?, r.get::<_,String>(1)?, r.get::<_,String>(2)?, r.get::<_,i64>(3)?, r.get::<_,Option<String>>(4)?))).unwrap();
        for row in rows { let (sn,it,pr,qt,nt) = row.unwrap(); w.write_record([&sn,&it,&pr,&qt.to_string(),&nt.unwrap_or_default()])?; }
        Ok(())
    })
}

fn export_party_items(conn: &rusqlite::Connection) -> Result<String, String> {
    csv_string(|w| {
        w.write_record(["item_name","owner","quantity","notes"])?;
        let mut s = conn.prepare("SELECT item_name,owner,quantity,notes FROM party_items ORDER BY owner,item_name").unwrap();
        let rows = s.query_map([], |r| Ok((r.get::<_,String>(0)?, r.get::<_,String>(1)?, r.get::<_,i64>(2)?, r.get::<_,Option<String>>(3)?))).unwrap();
        for row in rows { let (it,ow,qt,nt) = row.unwrap(); w.write_record([&it,&ow,&qt.to_string(),&nt.unwrap_or_default()])?; }
        Ok(())
    })
}

fn export_notes_csv(conn: &rusqlite::Connection) -> Result<String, String> {
    csv_string(|w| {
        w.write_record(["session_label","note_date","body"])?;
        let mut s = conn.prepare("SELECT session_label,note_date,body FROM notes ORDER BY session_label DESC,note_date DESC").unwrap();
        let rows = s.query_map([], |r| Ok((r.get::<_,String>(0)?, r.get::<_,String>(1)?, r.get::<_,String>(2)?))).unwrap();
        for row in rows { let (sl,nd,bo) = row.unwrap(); w.write_record([&sl,&nd,&bo])?; }
        Ok(())
    })
}

fn export_magic_items(conn: &rusqlite::Connection) -> Result<String, String> {
    csv_string(|w| {
        w.write_record(["name","item_type","rarity","requires_attunement","attunement_requirement","description","mechanical_effect","charges","source_campaign","tags"])?;
        let mut s = conn.prepare("SELECT name,item_type,rarity,requires_attunement,attunement_requirement,description,mechanical_effect,charges,source_campaign,tags FROM magic_items ORDER BY name").unwrap();
        let rows = s.query_map([], |r| Ok((r.get::<_,String>(0)?,r.get::<_,String>(1)?,r.get::<_,String>(2)?,r.get::<_,bool>(3)?,r.get::<_,Option<String>>(4)?,r.get::<_,String>(5)?,r.get::<_,String>(6)?,r.get::<_,Option<i64>>(7)?,r.get::<_,Option<String>>(8)?,r.get::<_,String>(9)?))).unwrap();
        for row in rows {
            let (nm,it,ra,at,ar,de,me,ch,sc,tg) = row.unwrap();
            w.write_record([&nm,&it,&ra,&at.to_string(),&ar.unwrap_or_default(),&de,&me,&ch.map(|v|v.to_string()).unwrap_or_default(),&sc.unwrap_or_default(),&tags_to_csv(&tg)])?;
        }
        Ok(())
    })
}

fn export_bestiary(conn: &rusqlite::Connection) -> Result<String, String> {
    csv_string(|w| {
        w.write_record(["name","ac","max_hp","initiative_mod","cr","statblock_md","tags"])?;
        let mut s = conn.prepare("SELECT name,ac,max_hp,initiative_mod,cr,statblock_md,tags FROM bestiary ORDER BY name").unwrap();
        let rows = s.query_map([], |r| Ok((r.get::<_,String>(0)?,r.get::<_,i64>(1)?,r.get::<_,i64>(2)?,r.get::<_,i64>(3)?,r.get::<_,String>(4)?,r.get::<_,String>(5)?,r.get::<_,String>(6)?))).unwrap();
        for row in rows {
            let (nm,ac,hp,im,cr,sb,tg) = row.unwrap();
            w.write_record([&nm,&ac.to_string(),&hp.to_string(),&im.to_string(),&cr,&sb,&tags_to_csv(&tg)])?;
        }
        Ok(())
    })
}

fn export_mechanics(conn: &rusqlite::Connection) -> Result<String, String> {
    csv_string(|w| {
        w.write_record(["title","body_md","campaign","tags"])?;
        let mut s = conn.prepare("SELECT title,body_md,campaign,tags FROM mechanics ORDER BY title").unwrap();
        let rows = s.query_map([], |r| Ok((r.get::<_,String>(0)?,r.get::<_,String>(1)?,r.get::<_,Option<String>>(2)?,r.get::<_,String>(3)?))).unwrap();
        for row in rows {
            let (ti,bo,ca,tg) = row.unwrap();
            w.write_record([&ti,&bo,&ca.unwrap_or_default(),&tags_to_csv(&tg)])?;
        }
        Ok(())
    })
}

fn export_campaigns(conn: &rusqlite::Connection) -> Result<String, String> {
    csv_string(|w| {
        w.write_record(["title","body_md","tags"])?;
        let mut s = conn.prepare("SELECT title,body_md,tags FROM campaigns ORDER BY title").unwrap();
        let rows = s.query_map([], |r| Ok((r.get::<_,String>(0)?,r.get::<_,String>(1)?,r.get::<_,String>(2)?))).unwrap();
        for row in rows {
            let (ti,bo,tg) = row.unwrap();
            w.write_record([&ti,&bo,&tags_to_csv(&tg)])?;
        }
        Ok(())
    })
}

// ── Import per-table ──────────────────────────────────────────────────────────

#[tauri::command]
pub fn import_csv(state: State<DbState>, table: String, csv_text: String) -> Result<CsvImportReport, String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    dispatch_import(&conn, &table, &csv_text)
}

fn dispatch_import(conn: &rusqlite::Connection, table: &str, csv_text: &str) -> Result<CsvImportReport, String> {
    match table {
        "players"     => import_players(conn, csv_text),
        "shops"       => import_shops(conn, csv_text),
        "party_items" => import_party_items(conn, csv_text),
        "notes"       => import_notes(conn, csv_text),
        "magic_items" => import_magic_items(conn, csv_text),
        "bestiary"    => import_bestiary(conn, csv_text),
        "mechanics"   => import_mechanics(conn, csv_text),
        "campaigns"   => import_campaigns(conn, csv_text),
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
        if rec.len() < 6 { r.skip(format!("row {}: expected ≥6 columns, got {}", i+2, rec.len())); continue; }
        let pn = rec[0].trim().to_string(); let cn = rec[1].trim().to_string();
        if pn.is_empty() || cn.is_empty() { r.skip(format!("row {}: player_name and character_name required", i+2)); continue; }
        let ac  = match parse_i64(rec[2].trim(), "ac",                i+2, &mut r) { Some(v)=>v, None=>continue };
        let mhp = match parse_i64(rec[3].trim(), "max_hp",            i+2, &mut r) { Some(v)=>v, None=>continue };
        let im  = match parse_i64(rec[4].trim(), "initiative_mod",    i+2, &mut r) { Some(v)=>v, None=>continue };
        let pp  = match parse_i64(rec[5].trim(), "passive_perception", i+2, &mut r) { Some(v)=>v, None=>continue };
        let nt: Option<String> = rec.get(6).map(|s| s.trim()).filter(|s| !s.is_empty()).map(String::from);
        match conn.execute("INSERT INTO players (player_name,character_name,ac,max_hp,initiative_mod,passive_perception,notes) VALUES (?1,?2,?3,?4,?5,?6,?7)", params![pn,cn,ac,mhp,im,pp,nt]) {
            Ok(_) => r.inserted += 1, Err(e) => r.skip(format!("row {}: db error: {e}", i+2)),
        }
    }
    Ok(r)
}

fn import_shops(conn: &rusqlite::Connection, csv_text: &str) -> Result<CsvImportReport, String> {
    let mut rdr = csv::Reader::from_reader(csv_text.as_bytes());
    let mut r = CsvImportReport::new();
    for (i, res) in rdr.records().enumerate() {
        let rec = match res { Ok(x) => x, Err(e) => { r.skip(format!("row {}: {e}", i+2)); continue; } };
        if rec.len() < 4 { r.skip(format!("row {}: expected ≥4 columns, got {}", i+2, rec.len())); continue; }
        let sn = rec[0].trim().to_string(); let it = rec[1].trim().to_string(); let pr = rec[2].trim().to_string();
        if sn.is_empty() || it.is_empty() { r.skip(format!("row {}: shop_name and item_name required", i+2)); continue; }
        let qt = match parse_i64(rec[3].trim(), "quantity", i+2, &mut r) { Some(v)=>v, None=>continue };
        if qt < 0 { r.skip(format!("row {}: quantity must be >= 0", i+2)); continue; }
        let nt: Option<String> = rec.get(4).map(|s| s.trim()).filter(|s| !s.is_empty()).map(String::from);
        match conn.execute("INSERT INTO shops (shop_name,item_name,price,quantity,notes) VALUES (?1,?2,?3,?4,?5)", params![sn,it,pr,qt,nt]) {
            Ok(_) => r.inserted += 1, Err(e) => r.skip(format!("row {}: db error: {e}", i+2)),
        }
    }
    Ok(r)
}

fn import_party_items(conn: &rusqlite::Connection, csv_text: &str) -> Result<CsvImportReport, String> {
    let mut rdr = csv::Reader::from_reader(csv_text.as_bytes());
    let mut r = CsvImportReport::new();
    for (i, res) in rdr.records().enumerate() {
        let rec = match res { Ok(x) => x, Err(e) => { r.skip(format!("row {}: {e}", i+2)); continue; } };
        if rec.len() < 3 { r.skip(format!("row {}: expected ≥3 columns, got {}", i+2, rec.len())); continue; }
        let it = rec[0].trim().to_string(); let ow = rec[1].trim().to_string();
        if it.is_empty() || ow.is_empty() { r.skip(format!("row {}: item_name and owner required", i+2)); continue; }
        let qt = match parse_i64(rec[2].trim(), "quantity", i+2, &mut r) { Some(v)=>v, None=>continue };
        if qt < 0 { r.skip(format!("row {}: quantity must be >= 0", i+2)); continue; }
        let nt: Option<String> = rec.get(3).map(|s| s.trim()).filter(|s| !s.is_empty()).map(String::from);
        match conn.execute("INSERT INTO party_items (item_name,owner,quantity,notes) VALUES (?1,?2,?3,?4)", params![it,ow,qt,nt]) {
            Ok(_) => r.inserted += 1, Err(e) => r.skip(format!("row {}: db error: {e}", i+2)),
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
        if rec.len() < 3 { r.skip(format!("row {}: expected ≥3 columns, got {}", i+2, rec.len())); continue; }
        let sl = rec[0].trim().to_string(); let nd = rec[1].trim().to_string(); let bo = rec[2].trim().to_string();
        if sl.is_empty() || nd.is_empty() || bo.is_empty() { r.skip(format!("row {}: all fields required", i+2)); continue; }
        match conn.execute("INSERT INTO notes (session_label,note_date,body,created_at) VALUES (?1,?2,?3,?4)", params![sl,nd,bo,now]) {
            Ok(_) => r.inserted += 1, Err(e) => r.skip(format!("row {}: db error: {e}", i+2)),
        }
    }
    Ok(r)
}

fn import_magic_items(conn: &rusqlite::Connection, csv_text: &str) -> Result<CsvImportReport, String> {
    let mut rdr = csv::Reader::from_reader(csv_text.as_bytes());
    let mut r = CsvImportReport::new();
    for (i, res) in rdr.records().enumerate() {
        let rec = match res { Ok(x) => x, Err(e) => { r.skip(format!("row {}: {e}", i+2)); continue; } };
        if rec.len() < 7 { r.skip(format!("row {}: expected ≥7 columns, got {}", i+2, rec.len())); continue; }
        let nm = rec[0].trim().to_string();
        if nm.is_empty() { r.skip(format!("row {}: name required", i+2)); continue; }
        let it = rec[1].trim().to_string();
        let ra = rec[2].trim().to_string();
        let at: bool = matches!(rec[3].trim().to_lowercase().as_str(), "true"|"1"|"yes");
        let ar: Option<String> = rec.get(4).map(|s| s.trim()).filter(|s| !s.is_empty()).map(String::from);
        let de = rec.get(5).map(|s| s.trim().to_string()).unwrap_or_default();
        let me = rec.get(6).map(|s| s.trim().to_string()).unwrap_or_default();
        let ch: Option<i64> = rec.get(7).and_then(|s| s.trim().parse().ok());
        let sc: Option<String> = rec.get(8).map(|s| s.trim()).filter(|s| !s.is_empty()).map(String::from);
        let tags = tags_to_json(&tags_from_csv(rec.get(9).unwrap_or("")));
        match conn.execute(
            "INSERT INTO magic_items (name,item_type,rarity,requires_attunement,attunement_requirement,description,mechanical_effect,charges,source_campaign,tags) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10)",
            params![nm,it,ra,at,ar,de,me,ch,sc,tags]) {
            Ok(_) => r.inserted += 1, Err(e) => r.skip(format!("row {}: db error: {e}", i+2)),
        }
    }
    Ok(r)
}

fn import_bestiary(conn: &rusqlite::Connection, csv_text: &str) -> Result<CsvImportReport, String> {
    let mut rdr = csv::Reader::from_reader(csv_text.as_bytes());
    let mut r = CsvImportReport::new();
    for (i, res) in rdr.records().enumerate() {
        let rec = match res { Ok(x) => x, Err(e) => { r.skip(format!("row {}: {e}", i+2)); continue; } };
        if rec.len() < 5 { r.skip(format!("row {}: expected ≥5 columns, got {}", i+2, rec.len())); continue; }
        let nm = rec[0].trim().to_string();
        if nm.is_empty() { r.skip(format!("row {}: name required", i+2)); continue; }
        let ac  = match parse_i64(rec[1].trim(), "ac",             i+2, &mut r) { Some(v)=>v, None=>continue };
        let hp  = match parse_i64(rec[2].trim(), "max_hp",         i+2, &mut r) { Some(v)=>v, None=>continue };
        let im  = match parse_i64(rec[3].trim(), "initiative_mod", i+2, &mut r) { Some(v)=>v, None=>continue };
        let cr  = rec.get(4).map(|s| s.trim().to_string()).unwrap_or_default();
        let sb  = rec.get(5).map(|s| s.trim().to_string()).unwrap_or_default();
        let tags = tags_to_json(&tags_from_csv(rec.get(6).unwrap_or("")));
        match conn.execute(
            "INSERT INTO bestiary (name,ac,max_hp,initiative_mod,cr,statblock_md,tags) VALUES (?1,?2,?3,?4,?5,?6,?7)",
            params![nm,ac,hp,im,cr,sb,tags]) {
            Ok(_) => r.inserted += 1, Err(e) => r.skip(format!("row {}: db error: {e}", i+2)),
        }
    }
    Ok(r)
}

fn import_mechanics(conn: &rusqlite::Connection, csv_text: &str) -> Result<CsvImportReport, String> {
    let mut rdr = csv::Reader::from_reader(csv_text.as_bytes());
    let mut r = CsvImportReport::new();
    for (i, res) in rdr.records().enumerate() {
        let rec = match res { Ok(x) => x, Err(e) => { r.skip(format!("row {}: {e}", i+2)); continue; } };
        if rec.len() < 2 { r.skip(format!("row {}: expected ≥2 columns, got {}", i+2, rec.len())); continue; }
        let ti = rec[0].trim().to_string(); let bo = rec[1].trim().to_string();
        if ti.is_empty() { r.skip(format!("row {}: title required", i+2)); continue; }
        let ca: Option<String> = rec.get(2).map(|s| s.trim()).filter(|s| !s.is_empty()).map(String::from);
        let tags = tags_to_json(&tags_from_csv(rec.get(3).unwrap_or("")));
        match conn.execute("INSERT INTO mechanics (title,body_md,campaign,tags) VALUES (?1,?2,?3,?4)", params![ti,bo,ca,tags]) {
            Ok(_) => r.inserted += 1, Err(e) => r.skip(format!("row {}: db error: {e}", i+2)),
        }
    }
    Ok(r)
}

fn import_campaigns(conn: &rusqlite::Connection, csv_text: &str) -> Result<CsvImportReport, String> {
    let mut rdr = csv::Reader::from_reader(csv_text.as_bytes());
    let mut r = CsvImportReport::new();
    for (i, res) in rdr.records().enumerate() {
        let rec = match res { Ok(x) => x, Err(e) => { r.skip(format!("row {}: {e}", i+2)); continue; } };
        if rec.len() < 2 { r.skip(format!("row {}: expected ≥2 columns, got {}", i+2, rec.len())); continue; }
        let ti = rec[0].trim().to_string(); let bo = rec[1].trim().to_string();
        if ti.is_empty() { r.skip(format!("row {}: title required", i+2)); continue; }
        let tags = tags_to_json(&tags_from_csv(rec.get(2).unwrap_or("")));
        match conn.execute("INSERT INTO campaigns (title,body_md,tags) VALUES (?1,?2,?3)", params![ti,bo,tags]) {
            Ok(_) => r.inserted += 1, Err(e) => r.skip(format!("row {}: db error: {e}", i+2)),
        }
    }
    Ok(r)
}

// ── Bulk folder/file import ───────────────────────────────────────────────────

/// Accepts a list of paths (files or directories). Directories are scanned for
/// *.csv files one level deep. Each file is auto-detected by headers then filename.
#[tauri::command]
pub fn import_paths(state: State<DbState>, paths: Vec<String>) -> Result<Vec<FileImportResult>, String> {
    let conn = state.0.lock().map_err(|e| e.to_string())?;
    let mut results: Vec<FileImportResult> = Vec::new();

    let mut csv_files: Vec<std::path::PathBuf> = Vec::new();
    for raw in &paths {
        let p = std::path::Path::new(raw);
        if p.is_dir() {
            let rd = std::fs::read_dir(p).map_err(|e| format!("cannot read dir '{raw}': {e}"))?;
            for entry in rd.flatten() {
                let ep = entry.path();
                if ep.extension().and_then(|e| e.to_str()).map(|e| e.eq_ignore_ascii_case("csv")).unwrap_or(false) {
                    csv_files.push(ep);
                }
            }
        } else if p.extension().and_then(|e| e.to_str()).map(|e| e.eq_ignore_ascii_case("csv")).unwrap_or(false) {
            csv_files.push(p.to_path_buf());
        }
    }

    csv_files.sort();

    for path in csv_files {
        let filename = path.file_name().and_then(|n| n.to_str()).unwrap_or("").to_string();
        let path_str = path.to_string_lossy().to_string();

        let csv_text = match std::fs::read_to_string(&path) {
            Ok(t) => t,
            Err(e) => {
                results.push(FileImportResult {
                    path: path_str, filename, table: "unknown".into(),
                    status: "error".into(), inserted: 0, skipped_rows: 0,
                    errors: vec![format!("could not read file: {e}")],
                });
                continue;
            }
        };

        let table = match detect_table(&filename, &csv_text) {
            Some(t) => t,
            None => {
                results.push(FileImportResult {
                    path: path_str, filename, table: "unknown".into(),
                    status: "unknown".into(), inserted: 0, skipped_rows: 0,
                    errors: vec!["could not detect table from headers or filename".into()],
                });
                continue;
            }
        };

        match dispatch_import(&conn, table, &csv_text) {
            Ok(rep) => results.push(FileImportResult {
                path: path_str, filename, table: table.into(),
                status: "ok".into(),
                inserted: rep.inserted, skipped_rows: rep.skipped, errors: rep.errors,
            }),
            Err(e) => results.push(FileImportResult {
                path: path_str, filename, table: table.into(),
                status: "error".into(), inserted: 0, skipped_rows: 0,
                errors: vec![e],
            }),
        }
    }

    Ok(results)
}
