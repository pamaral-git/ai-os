//! Universal SFT builder for ~/Documents/LoRA
//!
//! Converts every remaining (non `SFT_`) dataset folder into an MLX-LM ready
//! chat-SFT dataset: data/train/valid/test .jsonl plus an `sft_config.yaml`.
//! FIXED: test.jsonl no longer empty (was causing IndexError in mlx_lm)

use std::{
    fs::{self, File},
    io::{BufRead, BufReader, BufWriter, Write},
    path::{Path, PathBuf},
};

use anyhow::{Context, Result};
use clap::Parser;
use rand::{rngs::StdRng, seq::SliceRandom, SeedableRng};
use serde::Serialize;
use serde_json::{Map, Value};
use walkdir::WalkDir;

// ───────────────────────────── configuration ──────────────────────────────

const SFT_PREFIX: &str = "SFT_";
const EXCLUDED_DIRS: [&str; 3] = ["cloud-workspace", ".env", "-workspace"];
const SUPPORTED_EXTENSIONS: [&str; 5] = ["jsonl", "json", "parquet", "csv", "tsv"];

const MAX_FILES_PER_DATASET: usize = 20;
const MIN_FILE_BYTES: u64 = 100;
const SHUFFLE_SEED: u64 = 42;
const TRAIN_FRACTION: f64 = 0.9;

const MIN_TEXT_CHARS: usize = 20;
const MIN_FALLBACK_FIELD_CHARS: usize = 5;
const MAX_FALLBACK_PROMPT_CHARS: usize = 2000;

const BASE_MODEL: &str = "mlx-community/Qwen2.5-7B-Instruct-4bit";

type Record = Map<String, Value>;

// ───────────────────────────── output types ───────────────────────────────

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
enum Role {
    System,
    User,
    Assistant,
    Tool,
}

#[derive(Debug, Clone, Serialize)]
struct Message {
    role: Role,
    content: String,
}

impl Message {
    fn new(role: Role, content: impl Into<String>) -> Self {
        Self { role, content: content.into() }
    }
}

#[derive(Debug, Serialize)]
#[serde(untagged)]
enum Sample {
    Messages { messages: Vec<Message> },
    Text { text: String },
}

impl Sample {
    fn chat(user: String, assistant: String) -> Self {
        Sample::Messages {
            messages: vec![
                Message::new(Role::User, user),
                Message::new(Role::Assistant, assistant),
            ],
        }
    }
}

// ───────────────────── helpers ───────────────────────────

fn is_truthy(v: &Value) -> bool {
    match v {
        Value::Null => false,
        Value::Bool(b) => *b,
        Value::Number(n) => n.as_f64().map_or(true, |f| f != 0.0),
        Value::String(s) => !s.is_empty(),
        Value::Array(a) => !a.is_empty(),
        Value::Object(o) => !o.is_empty(),
    }
}

fn value_to_text(v: &Value) -> String {
    match v {
        Value::String(s) => s.clone(),
        Value::Null => String::new(),
        other => other.to_string(),
    }
}

fn clean_value(v: &Value) -> String {
    value_to_text(v).trim().to_owned()
}

fn get_truthy<'a>(rec: &'a Record, key: &str) -> Option<&'a Value> {
    rec.get(key).filter(|v| is_truthy(v))
}

fn first_truthy<'a>(rec: &'a Record, keys: &[&str]) -> Option<&'a Value> {
    keys.iter().find_map(|k| get_truthy(rec, k))
}

fn normalize_role(raw: &Value) -> Role {
    match value_to_text(raw).to_lowercase().as_str() {
        "system" | "system_prompt" => Role::System,
        "assistant" | "gpt" | "model" | "ai" | "output" | "answer" | "completion"
        | "response" => Role::Assistant,
        "tool" | "observation" | "tool_output" | "function" => Role::Tool,
        _ => Role::User,
    }
}

fn flatten_content(content: &Value) -> String {
    match content {
        Value::Array(parts) => parts
            .iter()
            .map(|part| match part {
                Value::Object(o) => o.get("text").map(value_to_text).unwrap_or_default(),
                other => value_to_text(other),
            })
            .collect::<Vec<_>>()
            .join("\n"),
        other => value_to_text(other),
    }
}

fn parse_turn(turn: &Value) -> Option<Message> {
    const KEY_PAIRS: [(&str, &str); 3] =
        [("from", "value"), ("role", "content"), ("role", "value")];

    let obj = turn.as_object()?;
    let (role_key, content_key) = KEY_PAIRS
        .iter()
        .find(|(r, c)| obj.contains_key(*r) && obj.contains_key(*c))?;

    let content = &obj[*content_key];
    if !is_truthy(content) {
        return None;
    }
    Some(Message::new(
        normalize_role(&obj[*role_key]),
        flatten_content(content).trim(),
    ))
}

fn convert_turns(turns: &[Value]) -> Vec<Message> {
    turns.iter().filter_map(parse_turn).collect()
}

fn inject_tools(messages: &mut Vec<Message>, tools: &Value) {
    let tools_text = match tools {
        Value::String(s) => s.clone(),
        other => other.to_string(),
    };
    let preamble = format!("You have access to these tools:\n{tools_text}");

    if messages.first().is_some_and(|m| m.role == Role::System) {
        messages[0].content = format!("{preamble}\n\n{}", messages[0].content);
    } else {
        messages.insert(0, Message::new(Role::System, preamble));
    }
}

// ───────────────────── strategies ─────────────────────────

fn from_messages(rec: &Record) -> Option<Sample> {
    let messages = convert_turns(rec.get("messages")?.as_array()?);
    (!messages.is_empty()).then(|| Sample::Messages { messages })
}

fn from_conversations(rec: &Record) -> Option<Sample> {
    let mut messages = convert_turns(rec.get("conversations")?.as_array()?);
    if messages.is_empty() {
        return None;
    }
    if let Some(tools) = get_truthy(rec, "tools") {
        inject_tools(&mut messages, tools);
    }
    Some(Sample::Messages { messages })
}

fn from_instruction(rec: &Record) -> Option<Sample> {
    let instruction = rec.get("instruction")?;
    let output = first_truthy(rec, &["output", "response", "answer"])?;

    let mut prompt = value_to_text(instruction);
    if let Some(input) = first_truthy(rec, &["input", "context"]) {
        prompt.push_str("\n\nInput:\n");
        prompt.push_str(&value_to_text(input));
    }
    Some(Sample::chat(prompt.trim().to_owned(), clean_value(output)))
}

const PROMPT_PAIRS: &[(&str, &str)] = &[
    ("question", "answer"),
    ("prompt", "completion"),
    ("prompt", "response"),
    ("query", "answer"),
    ("problem", "solution"),
];

fn from_prompt_pairs(rec: &Record) -> Option<Sample> {
    PROMPT_PAIRS.iter().find_map(|&(p_key, c_key)| {
        let prompt = get_truthy(rec, p_key)?;
        let completion = get_truthy(rec, c_key)?;

        let mut completion_text = value_to_text(completion);
        if let Some(thinking) = first_truthy(rec, &["thinking", "reasoning", "thought"]) {
            completion_text =
                format!("<think>{}</think>\n\n{completion_text}", value_to_text(thinking));
        }
        Some(Sample::chat(clean_value(prompt), completion_text.trim().to_owned()))
    })
}

const TRANSLATION_PAIRS: &[(&str, &str, &str)] = &[
    ("source", "target", "Translate to Portuguese:"),
    ("en", "pt", "Translate this English text to Portuguese (pt-PT):"),
];

fn from_translation(rec: &Record) -> Option<Sample> {
    TRANSLATION_PAIRS.iter().find_map(|&(src_key, tgt_key, instruction)| {
        let source = rec.get(src_key)?;
        let target = rec.get(tgt_key)?;
        Some(Sample::chat(
            format!("{instruction}\n{}", value_to_text(source)),
            clean_value(target),
        ))
    })
}

fn from_text(rec: &Record) -> Option<Sample> {
    let text = rec.get("text")?.as_str()?;
    (text.chars().count() > MIN_TEXT_CHARS).then(|| Sample::Text { text: text.to_owned() })
}

fn from_longest_string_fields(rec: &Record) -> Option<Sample> {
    let mut fields: Vec<(usize, &str)> = rec
        .values()
        .filter_map(Value::as_str)
        .map(|s| (s.chars().count(), s))
        .filter(|(len, _)| *len > MIN_FALLBACK_FIELD_CHARS)
        .collect();
    if fields.len() < 2 {
        return None;
    }
    fields.sort_by_key(|(len, _)| *len);

    let prompt: String = fields[0].1.chars().take(MAX_FALLBACK_PROMPT_CHARS).collect();
    let answer = fields[fields.len() - 1].1.to_owned();
    Some(Sample::chat(prompt, answer))
}

const STRATEGIES: &[fn(&Record) -> Option<Sample>] = &[
    from_messages,
    from_conversations,
    from_instruction,
    from_prompt_pairs,
    from_translation,
    from_text,
    from_longest_string_fields,
];

fn record_to_sample(rec: &Record) -> Option<Sample> {
    STRATEGIES.iter().find_map(|strategy| strategy(rec))
}

// ───────────────────────────── file loading ───────────────────────────────

fn only_objects(values: Vec<Value>) -> Vec<Record> {
    values
        .into_iter()
        .filter_map(|v| match v {
            Value::Object(map) => Some(map),
            _ => None,
        })
        .collect()
}

fn extension_of(path: &Path) -> Option<String> {
    Some(path.extension()?.to_str()?.to_ascii_lowercase())
}

fn extension_rank(path: &Path) -> Option<usize> {
    let ext = extension_of(path)?;
    SUPPORTED_EXTENSIONS.iter().position(|&e| e == ext)
}

fn load_jsonl(path: &Path) -> Result<Vec<Record>> {
    let reader = BufReader::new(File::open(path)?);
    let mut records = Vec::new();
    for line in reader.split(b'\n') {
        let line = line?;
        if line.iter().all(u8::is_ascii_whitespace) {
            continue;
        }
        if let Ok(Value::Object(map)) = serde_json::from_slice::<Value>(&line) {
            records.push(map);
        }
    }
    Ok(records)
}

fn load_json(path: &Path) -> Result<Vec<Record>> {
    let value: Value = serde_json::from_reader(BufReader::new(File::open(path)?))?;
    let items = match value {
        Value::Array(items) => items,
        Value::Object(mut obj) => {
            let data = obj.get_mut("data").and_then(Value::as_array_mut).map(std::mem::take);
            data.unwrap_or_else(|| vec![Value::Object(obj)])
        }
        _ => Vec::new(),
    };
    Ok(only_objects(items))
}

fn load_delimited(path: &Path, delimiter: u8) -> Result<Vec<Record>> {
    let mut reader = csv::ReaderBuilder::new()
        .delimiter(delimiter)
        .flexible(true)
        .from_path(path)?;
    let headers = reader.headers()?.clone();

    let mut records = Vec::new();
    for row in reader.records() {
        let row = row?;
        let record: Record = headers
            .iter()
            .zip(row.iter())
            .map(|(k, v)| (k.to_owned(), Value::String(v.to_owned())))
            .collect();
        records.push(record);
    }
    Ok(records)
}

#[cfg(feature = "parquet")]
fn load_parquet(path: &Path) -> Result<Vec<Record>> {
    use parquet::file::reader::{FileReader, SerializedFileReader};

    let reader = SerializedFileReader::new(File::open(path)?)?;
    let mut records = Vec::new();
    for row in reader.get_row_iter(None)? {
        if let Value::Object(map) = row?.to_json_value() {
            records.push(map);
        }
    }
    Ok(records)
}

#[cfg(not(feature = "parquet"))]
fn load_parquet(path: &Path) -> Result<Vec<Record>> {
    println!("  Parquet support not compiled in, skipping {}", path.display());
    Ok(Vec::new())
}

fn load_records(path: &Path) -> Result<Vec<Record>> {
    match extension_of(path).as_deref() {
        Some("jsonl") => load_jsonl(path),
        Some("json") => load_json(path),
        Some("parquet") => load_parquet(path),
        Some("csv") => load_delimited(path, b','),
        Some("tsv") => load_delimited(path, b'\t'),
        _ => Ok(Vec::new()),
    }
}

fn dir_name(path: &Path) -> String {
    path.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default()
}

fn find_data_files(folder: &Path) -> Vec<PathBuf> {
    let mut files: Vec<(usize, PathBuf)> = WalkDir::new(folder)
        .follow_links(true)
        .into_iter()
        .filter_map(Result::ok)
        .filter(|e| e.file_type().is_file())
        .filter_map(|e| {
            let rank = extension_rank(e.path())?;
            let big_enough = e.metadata().map(|m| m.len() > MIN_FILE_BYTES).unwrap_or(false);
            if big_enough {
                Some((rank, e.into_path()))
            } else {
                None
            }
        })
        .collect();
    files.sort();
    files.into_iter().map(|(_, p)| p).collect()
}

fn load_all(files: &[PathBuf]) -> Vec<Record> {
    if files.len() > MAX_FILES_PER_DATASET {
        println!(
            "  Note: using only the first {MAX_FILES_PER_DATASET} of {} files",
            files.len()
        );
    }
    let mut all = Vec::new();
    for path in files.iter().take(MAX_FILES_PER_DATASET) {
        match load_records(path) {
            Ok(recs) => {
                println!("  {}: {} records", dir_name(path), recs.len());
                all.extend(recs);
            }
            Err(e) => println!("  Failed {}: {e:#}", path.display()),
        }
    }
    all
}

fn split_train_valid<T>(items: &[T]) -> (&[T], &[T]) {
    items.split_at((items.len() as f64 * TRAIN_FRACTION) as usize)
}

fn write_jsonl<T: Serialize>(path: &Path, items: &[T]) -> Result<()> {
    let file = File::create(path).with_context(|| format!("creating {}", path.display()))?;
    let mut w = BufWriter::new(file);
    for item in items {
        serde_json::to_writer(&mut w, item)?;
        w.write_all(b"\n")?;
    }
    w.flush()?;
    Ok(())
}

fn render_config(out_name: &str) -> String {
    format!(
        r#"model: "{BASE_MODEL}"
train: true
fine_tune_type: lora
batch_size: 2
iters: 600
learning_rate: 1e-05
mask_prompt: true
adapter_path: "./{out_name}_adapters"
data: "{out_name}"
"#
    )
}

fn write_dataset(
    out_dir: &Path,
    out_name: &str,
    all: &[Sample],
    train: &[Sample],
    valid: &[Sample],
) -> Result<()> {
    fs::create_dir_all(out_dir)?;
    write_jsonl(&out_dir.join("data.jsonl"), all)?;
    write_jsonl(&out_dir.join("train.jsonl"), train)?;
    write_jsonl(&out_dir.join("valid.jsonl"), valid)?;
    // FIXED: was empty file -> caused IndexError: list index out of range
    // Now copy 1 record from valid (or train) so mlx_lm never sees empty file
    let test_src = if !valid.is_empty() { valid } else { train };
    let test_one = &test_src[..test_src.len().min(1)];
    write_jsonl(&out_dir.join("test.jsonl"), test_one)?;
    fs::write(out_dir.join("sft_config.yaml"), render_config(out_name))?;
    Ok(())
}

fn process_dataset(src: &Path, out_root: &Path) -> Result<bool> {
    let name = dir_name(src);
    println!("\n=== Processing {name} ===");

    let files = find_data_files(src);
    if files.is_empty() {
        println!("  No data files found in {}", src.display());
        return Ok(false);
    }

    let raw = load_all(&files);
    if raw.is_empty() {
        return Ok(false);
    }

    let mut samples: Vec<Sample> = raw.iter().filter_map(record_to_sample).collect();
    if samples.is_empty() {
        let keys: Vec<&String> = raw[0].keys().take(20).collect();
        println!("  Could not convert, sample keys: {keys:?}");
        return Ok(false);
    }
    println!("  Converted {}/{} -> SFT chat format", samples.len(), raw.len());

    samples.shuffle(&mut StdRng::seed_from_u64(SHUFFLE_SEED));
    let (train, valid) = split_train_valid(&samples);

    let out_name = format!("{SFT_PREFIX}{}", name.replace('-', "_"));
    let out_dir = out_root.join(&out_name);
    write_dataset(&out_dir, &out_name, &samples, train, valid)?;

    println!(
        "  -> Wrote {} : train={} valid={} test=1 (fixed)",
        out_dir.display(),
        train.len(),
        valid.len()
    );
    Ok(true)
}

#[derive(Parser)]
#[command(about = "Convert all non-SFT_ dataset folders into MLX-LM SFT format")]
struct Args {
    #[arg(long = "lora_dir", alias = "lora-dir", default_value = ".")]
    lora_dir: String,
}

fn expand_tilde(path: &str) -> PathBuf {
    if path == "~" || path.starts_with("~/") {
        if let Some(home) = std::env::var_os("HOME") {
            return Path::new(&home).join(path[1..].trim_start_matches('/'));
        }
    }
    PathBuf::from(path)
}

fn discover_datasets(root: &Path) -> Result<Vec<PathBuf>> {
    let mut dirs: Vec<PathBuf> = fs::read_dir(root)
        .with_context(|| format!("cannot read {}", root.display()))?
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| p.is_dir())
        .collect();
    dirs.sort();

    let mut datasets = Vec::new();
    for path in dirs {
        let name = dir_name(&path);
        if name.starts_with(SFT_PREFIX) {
            println!("Skipping already SFT: {name}");
        } else if name.starts_with('.') || EXCLUDED_DIRS.contains(&name.as_str()) {
            // ignored
        } else {
            datasets.push(path);
        }
    }
    Ok(datasets)
}

fn main() -> Result<()> {
    let args = Args::parse();

    let lora_root = expand_tilde(&args.lora_dir)
        .canonicalize()
        .with_context(|| format!("LoRA dir not found: {}", args.lora_dir))?;

    let datasets = discover_datasets(&lora_root)?;
    println!(
        "Found {} remaining datasets to convert in {}",
        datasets.len(),
        lora_root.display()
    );

    for folder in &datasets {
        if let Err(err) = process_dataset(folder, &lora_root) {
            eprintln!("  Error processing {}: {err:#}", folder.display());
        }
    }

    println!("\nDone! Train any with: mlx_lm.lora --config SFT_<name>/sft_config.yaml");
    Ok(())
}
