use rand::Rng;
use serde::Serialize;

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct RollResult {
    pub expr: String,
    pub all_rolls: Vec<u32>,
    pub kept_rolls: Vec<u32>,
    pub modifier: i64,
    pub total: i64,
}

struct DiceExpr {
    count: u32,
    sides: u32,
    modifier: i64,
    advantage: bool,
    disadvantage: bool,
}

fn parse_expr(raw: &str) -> Result<DiceExpr, String> {
    let s = raw.trim().to_lowercase();

    let (s, advantage, disadvantage) = if s.ends_with("adv") {
        (s[..s.len() - 3].to_string(), true, false)
    } else if s.ends_with("dis") {
        (s[..s.len() - 3].to_string(), false, true)
    } else {
        (s.clone(), false, false)
    };

    let d_pos = s.find('d').ok_or_else(|| format!("no 'd' in expression '{raw}'"))?;
    let count_s = &s[..d_pos];
    let rest = &s[d_pos + 1..];

    let count: u32 = if count_s.is_empty() {
        1
    } else {
        count_s.parse().map_err(|_| format!("invalid die count '{count_s}'"))?
    };

    // find +/- for modifier, but only after the sides digits
    let (sides_s, modifier): (&str, i64) = if let Some(pos) = rest.find(['+', '-']) {
        let sign: i64 = if rest.as_bytes()[pos] == b'-' { -1 } else { 1 };
        let mag: i64 = rest[pos + 1..].parse().map_err(|_| "invalid modifier".to_string())?;
        (&rest[..pos], sign * mag)
    } else {
        (rest, 0)
    };

    let sides: u32 = sides_s.parse().map_err(|_| format!("invalid die sides '{sides_s}'"))?;
    if sides < 1 {
        return Err("die must have at least 1 side".into());
    }
    if count < 1 {
        return Err("must roll at least 1 die".into());
    }

    Ok(DiceExpr { count, sides, modifier, advantage, disadvantage })
}

fn roll_set(count: u32, sides: u32) -> Vec<u32> {
    let mut rng = rand::thread_rng();
    (0..count).map(|_| rng.gen_range(1..=sides)).collect()
}

#[tauri::command]
pub fn roll(expr: String) -> Result<RollResult, String> {
    let d = parse_expr(&expr)?;

    let (all_rolls, kept_rolls) = if d.advantage || d.disadvantage {
        let r1 = roll_set(d.count, d.sides);
        let r2 = roll_set(d.count, d.sides);
        let s1: u32 = r1.iter().sum();
        let s2: u32 = r2.iter().sum();
        let keep_first = if d.advantage { s1 >= s2 } else { s1 <= s2 };
        let kept = if keep_first { r1.clone() } else { r2.clone() };
        let mut all = r1;
        all.extend(r2);
        (all, kept)
    } else {
        let r = roll_set(d.count, d.sides);
        (r.clone(), r)
    };

    let total: i64 = kept_rolls.iter().map(|&x| x as i64).sum::<i64>() + d.modifier;

    Ok(RollResult { expr, all_rolls, kept_rolls, modifier: d.modifier, total })
}
