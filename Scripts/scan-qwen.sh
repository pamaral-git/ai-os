#!/usr/bin/env bash
# scan-qwen.sh — look for strings from the Qwen3.8 reports in your own
# logs, chats, histories, and model metadata.
#
#   https://cohere.com/blog/concerning-behaviour-popular-open-weight-ai-model
#
# A hit means the string is in a file you scanned. It does not, by itself, mean
# a request left this machine: saved write-ups, this script under another name,
# and blocker plugins contain the same strings. Read the path.
#
# A miss does not clear the weights. The behaviour is a sampling habit. The
# routify attractor lives in a hashed n-gram table, not as plaintext in the
# tensors, so grepping a GGUF cannot prove the model is clean.
#
# Exit status:
#   0  nothing from the lists below
#   1  high-confidence incident string
#   2  the scan did not finish (missing rg, bad path, rg error)
#   3  only broad or command-shape hits, which need a human
#      (--strict turns 3 into 1)
#
# Needs ripgrep 13+ (brew install ripgrep). python3 is optional and is what
# keeps the model pass on metadata instead of tensor bytes. Bash 3.2 safe.
set -u

usage() {
  cat <<'EOF'
Usage: scan-qwen.sh [options] [path ...]

No paths: scan the default locations that exist (models, llama-swap config,
shell history, Library logs, opencode/crow session dirs).

Options:
  -L, --follow            follow symlinks found while walking a directory
                         (a symlink you pass by name is always read)
  --strict                broad and command-shape hits exit 1
  --max-count N           max matches per file per pass (default 40)
  --max-filesize SIZE     skip larger text files: 10, 512K, 1M, 1G (default 1G)
  -h, --help

High (exit 1) — incident-specific, not normal cloud docs:
  PROBE_PAYLOAD_ABC123     Cohere probe body
  sanmaohe                 Beijing bucket label from that capture
  routify…file…            relay-host family (proxy, oversea, .io mutants)
  proxy_temp_file/production
                           object prefix on the fabricated signed URLs
  /tmp/put_probe           where the probe saved the response
  aliyuncs.io              mutant TLD, not Aliyun's real OSS domain

Broad (exit 3) — read the file; these are common in real configs and docs:
  aliyuncs.com             Aliyun / OSS
  169.254.169.254          AWS / GCP / Azure metadata
  100.100.100.200          Aliyun metadata

Shape (exit 3) — same log line only, and only the combination from the
offline episode. Plain "unshare -Urm" is a normal rootless-container command
and is not reported.
EOF
}

die() { printf '%s\n' "$1" >&2; exit 2; }

FOLLOW=0
STRICT=0
MAX_COUNT=40
MAX_FILESIZE=1G
TARGETS=()

while [ "$#" -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    -L|--follow) FOLLOW=1 ;;
    --strict) STRICT=1 ;;
    --max-count)
      shift
      [ "$#" -gt 0 ] || die "--max-count needs a number"
      MAX_COUNT=$1
      ;;
    --max-count=*) MAX_COUNT=${1#--max-count=} ;;
    --max-filesize)
      shift
      [ "$#" -gt 0 ] || die "--max-filesize needs a size"
      MAX_FILESIZE=$1
      ;;
    --max-filesize=*) MAX_FILESIZE=${1#--max-filesize=} ;;
    --) shift; while [ "$#" -gt 0 ]; do TARGETS+=("$1"); shift; done; break ;;
    -*) die "unknown option: $1" ;;
    *) TARGETS+=("$1") ;;
  esac
  shift
done

case "$MAX_COUNT" in
  ''|*[!0-9]*) die "--max-count must be a positive integer" ;;
esac
[ "$MAX_COUNT" -gt 0 ] || die "--max-count must be a positive integer"
[ -n "$MAX_FILESIZE" ] || die "--max-filesize must not be empty"

command -v rg >/dev/null 2>&1 || die "ripgrep (rg) not found: brew install ripgrep"
if ! rg --help 2>/dev/null | grep -q glob-case-insensitive; then
  die "rg is too old; need ripgrep 13+ (glob-case-insensitive)"
fi

# Regexes, not literals. Add new ones already escaped.
# High: no business in your own logs unless you saved the write-up.
HIGH_PARTS=(
  '\bPROBE_PAYLOAD_ABC123\b'
  '\bsanmaohe\b'
  '\broutify[-_.[:alnum:]]{0,32}file'
  'proxy_temp_file/production'
  '/tmp/put_probe'
  '\baliyuncs\.io\b'
)
# Broad: legitimate Aliyun configs, cloud-init, and security docs.
BROAD_PARTS=(
  '\baliyuncs\.com\b'
  '\b169\.254\.169\.254\b'
  '\b100\.100\.100\.200\b'
)
# Capital U is the user namespace. Do not case-fold this one.
SHAPE_PARTS=(
  'unshare[[:space:]]+-[A-Za-z]*U[A-Za-z]*[^\n]{0,180}(?:--propagation[[:space:]]+private|mount[[:space:]]+-t[[:space:]]+tmpfs)'
)

SELF=$(basename -- "$0")
case "$SELF" in
  *[][*?]*) SELF="" ;;
esac

if [ "${#TARGETS[@]}" -eq 0 ]; then
  for p in \
    "$HOME/models" \
    "/Volumes/X-Drive" \
    "$HOME/Documents/cloud-workspace" \
    "$HOME/.config/llama-swap" \
    "$HOME/Library/Logs" \
    "$HOME/.zsh_history" \
    "$HOME/.bash_history" \
    "$HOME/.local/share/opencode" \
    "$HOME/.config/opencode" \
    "$HOME/.local/state/crow" \
    "$HOME/.local/share/crow"
  do
    [ -e "$p" ] && TARGETS+=("$p")
  done
fi
[ "${#TARGETS[@]}" -gt 0 ] || die "No targets found; pass paths as arguments."

for t in "${TARGETS[@]}"; do
  [ -e "$t" ] || die "not found: $t"
done

umask 077
tmpdir=
cleanup() {
  if [ -n "${tmpdir:-}" ] && [ -d "$tmpdir" ]; then
    rm -rf "$tmpdir"
  fi
}
trap cleanup EXIT
tmpdir=$(mktemp -d "${TMPDIR:-/tmp}/.qwen-iocs.XXXXXX") || die "mktemp failed"

PY_OK=0
command -v python3 >/dev/null 2>&1 && PY_OK=1

high_n=0
broad_n=0
shape_n=0
scan_err=0
models_n=0
raw_n=0

window() {
  # 100 chars of the same line on either side, so a sqlite page is not printed whole.
  printf '%s' '[^\n]{0,100}?'"$1"'[^\n]{0,100}'
}

file_bytes() {
  stat -c %s "$1" 2>/dev/null || stat -f %z "$1" 2>/dev/null
}

size_to_bytes() {
  # Integer plus an optional K/M/G, matching rg's --max-filesize. No decimals.
  local s=$1 n unit
  s=$(printf '%s' "$s" | tr '[:lower:]' '[:upper:]')
  case "$s" in
    *[!0-9KMG]*) return 1 ;;
  esac
  n=${s%[KMG]}
  unit=${s#"$n"}
  case "$n" in
    ''|*[!0-9]*) return 1 ;;
  esac
  case "$unit" in
    '') printf '%s' "$n" ;;
    K) printf '%s' $((n * 1024)) ;;
    M) printf '%s' $((n * 1024 * 1024)) ;;
    G) printf '%s' $((n * 1024 * 1024 * 1024)) ;;
    *) return 1 ;;
  esac
}

kind_of() {
  local l
  l=$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')
  case "$l" in
    *.gguf|*.safetensors) printf '%s' header ;;
    *.bin|*.pt|*.pth|*.npy|*.npz|*.onnx|*.ckpt|*.ggml|*.img|*.dmg|*.iso) printf '%s' skip ;;
    *) printf '%s' text ;;
  esac
}

RG_COMMON=(
  -a -n -o
  --no-heading --with-filename --color=never
  --hidden --no-ignore --no-unicode --glob-case-insensitive
  --max-count "$MAX_COUNT"
  --max-filesize "$MAX_FILESIZE"
  -g '!**/.git/**'
  -g '!**/node_modules/**'
  -g '!**/.venv/**'
  -g '!**/venv/**'
  -g '!*.gguf' -g '!*.safetensors'
  -g '!*.bin' -g '!*.pt' -g '!*.pth' -g '!*.npy' -g '!*.npz'
  -g '!*.onnx' -g '!*.ckpt' -g '!*.ggml'
  -g '!*.png' -g '!*.jpg' -g '!*.jpeg' -g '!*.gif' -g '!*.webp'
  -g '!*.zip' -g '!*.gz' -g '!*.tgz' -g '!*.xz' -g '!*.7z' -g '!*.zst'
  -g '!*.pdf' -g '!*.parquet' -g '!*.arrow'
  -g '!*.img' -g '!*.dmg' -g '!*.iso'
  -g '!**/.qwen-iocs.*/**'
)
[ -n "$SELF" ] && RG_COMMON+=(-g "!$SELF")
[ "$FOLLOW" -eq 1 ] && RG_COMMON+=(-L)

note_rg_err() {
  local errf=$1 ec=$2
  if [ -s "$errf" ]; then
    printf 'rg warning/error:\n' >&2
    cat "$errf" >&2
  fi
  if [ "$ec" -ge 2 ]; then
    scan_err=1
  fi
}

# $1 label  $2 high|broad|shape  $3... regexes
run_pass() {
  local label=$1 sev=$2
  shift 2
  local -a res=()
  local p out errf ec n
  for p in "$@"; do
    res+=(-e "$(window "$p")")
  done
  out=$tmpdir/pass-$sev.out
  errf=$tmpdir/pass-$sev.err
  : >"$out"
  : >"$errf"
  printf '== %s ==\n' "$label"
  if [ "$sev" = "shape" ]; then
    LC_ALL=C rg "${RG_COMMON[@]}" "${res[@]}" -- "${SEARCH_TARGETS[@]}" >"$out" 2>"$errf"
  else
    LC_ALL=C rg "${RG_COMMON[@]}" -i "${res[@]}" -- "${SEARCH_TARGETS[@]}" >"$out" 2>"$errf"
  fi
  ec=$?
  # NUL would hide the rest of a binary match from the terminal.
  if [ -s "$out" ]; then
    tr '\000' '?' <"$out" >"$out.clean"
    mv "$out.clean" "$out"
  fi
  note_rg_err "$errf" "$ec"
  if [ "$ec" -eq 0 ]; then
    cat "$out"
    n=$(wc -l <"$out" | tr -d '[:space:]')
    printf '(matches: %s, capped at %s per file)\n' "$n" "$MAX_COUNT"
    case "$sev" in
      high) high_n=$((high_n + n)) ;;
      broad) broad_n=$((broad_n + n)) ;;
      shape) shape_n=$((shape_n + n)) ;;
    esac
  elif [ "$ec" -eq 1 ]; then
    printf '(no matches)\n'
  else
    printf '(search failed, exit %s)\n' "$ec"
  fi
  printf '\n'
}

extract_header() {
  # stdout: metadata text only. exit 0 on a parsed header, else caller falls back.
  python3 - "$1" <<'PY'
import struct, sys

path = sys.argv[1]
f = open(path, "rb")
LIMIT = 64 * 1024 * 1024
SIZES = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}

def take(n):
    b = f.read(n)
    if len(b) != n:
        raise EOFError("short read")
    if f.tell() > LIMIT:
        raise ValueError("header larger than 64MB")
    return b

def u32():
    return struct.unpack("<I", take(4))[0]

def u64():
    return struct.unpack("<Q", take(8))[0]

def read_string():
    n = u64()
    if n > 8 * 1024 * 1024:
        raise ValueError("string longer than 8MB")
    return take(n)

def emit(key, raw):
    text = raw.decode("utf-8", "replace")
    text = text.replace("\t", " ").replace("\r", "\\r").replace("\n", "\\n")
    sys.stdout.buffer.write((key + "\t" + text + "\n").encode("utf-8", "replace"))

def walk(vtype, key, depth):
    if depth > 6:
        raise ValueError("nested too deep")
    if vtype == 8:
        raw = read_string()
        # Array entries shorter than 4 bytes are tokenizer noise; scalar
        # strings (names, chat templates) are always kept.
        if depth == 0 or len(raw) >= 4:
            emit(key, raw)
        return
    if vtype == 9:
        et = u32()
        ln = u64()
        if ln > 5000000:
            raise ValueError("array longer than 5000000")
        for i in range(ln):
            walk(et, "%s[%d]" % (key, i), depth + 1)
        return
    if vtype not in SIZES:
        raise ValueError("unknown gguf type %s" % vtype)
    take(SIZES[vtype])

def parse_gguf():
    version = u32()
    if version < 2 or version > 4:
        sys.exit(2)
    n_tensors = u64()
    n_kv = u64()
    if n_tensors > 1000000 or n_kv > 1000000:
        sys.exit(2)
    sys.stdout.buffer.write(b"# format\tgguf\n")
    sys.stdout.buffer.write(("# tensors declared\t%d\n" % n_tensors).encode("ascii"))
    for _ in range(n_kv):
        key = read_string().decode("utf-8", "replace")
        key = key.replace("\t", " ").replace("\n", " ")
        walk(u32(), key, 0)

def parse_safetensors():
    f.seek(0)
    n = u64()
    if n == 0 or n > LIMIT:
        sys.exit(2)
    header = take(n)
    if not header.lstrip().startswith(b"{"):
        sys.exit(2)
    sys.stdout.buffer.write(b"# format\tsafetensors\n")
    sys.stdout.buffer.write(header)
    if not header.endswith(b"\n"):
        sys.stdout.buffer.write(b"\n")

def main():
    magic = take(4)
    if magic == b"GGUF":
        parse_gguf()
        return
    parse_safetensors()

try:
    main()
except SystemExit:
    raise
except Exception as e:
    sys.stderr.write("parse: %s\n" % e)
    sys.exit(1)
PY
}

hdr_field() {
  # $1 exact key, $2 TSV file. Values may contain tabs; the key will not.
  awk -F '\t' -v k="$1" '
    index($0, "\t") > 0 && substr($0, 1, index($0, "\t") - 1) == k {
      print substr($0, index($0, "\t") + 1)
      exit
    }
  ' "$2"
}

count_hits() {
  local sev=$1 file=$2
  local n
  [ -s "$file" ] || return 0
  n=$(wc -l <"$file" | tr -d '[:space:]')
  [ -n "$n" ] || return 0
  case "$sev" in
    high) high_n=$((high_n + n)) ;;
    broad) broad_n=$((broad_n + n)) ;;
    shape) shape_n=$((shape_n + n)) ;;
  esac
  while IFS= read -r line || [ -n "$line" ]; do
    printf '   [%s] %s\n' "$(printf '%s' "$sev" | tr '[:lower:]' '[:upper:]')" "$line"
  done <"$file"
}

scan_header_text() {
  local hdr=$1
  local sev p out errf ec
  local -a parts=() res=()
  for sev in high broad shape; do
    case "$sev" in
      high) parts=("${HIGH_PARTS[@]}") ;;
      broad) parts=("${BROAD_PARTS[@]}") ;;
      shape) parts=("${SHAPE_PARTS[@]}") ;;
    esac
    res=()
    for p in "${parts[@]}"; do
      res+=(-e "$(window "$p")")
    done
    out=$tmpdir/hdr-$sev.out
    errf=$tmpdir/hdr-$sev.err
    : >"$out"
    if [ "$sev" = "shape" ]; then
      LC_ALL=C rg -a -n -o --no-heading --no-filename --color=never --no-unicode \
        --max-count 20 "${res[@]}" "$hdr" >"$out" 2>"$errf"
    else
      LC_ALL=C rg -a -n -o -i --no-heading --no-filename --color=never --no-unicode \
        --max-count 20 "${res[@]}" "$hdr" >"$out" 2>"$errf"
    fi
    ec=$?
    if [ "$ec" -ge 2 ]; then
      scan_err=1
      note_rg_err "$errf" "$ec"
    fi
    count_hits "$sev" "$out"
  done
}

scan_one_model() {
  local f=$1 hdr=$tmpdir/hdr.txt pyerr=$tmpdir/py.err
  local mode name arch tensors qwen
  models_n=$((models_n + 1))
  printf '%s\n' "$f"
  if [ ! -r "$f" ]; then
    printf '   unreadable\n'
    scan_err=1
    return
  fi
  mode=raw
  : >"$pyerr"
  if [ "$PY_OK" -eq 1 ] && extract_header "$f" >"$hdr" 2>"$pyerr"; then
    mode=parsed
  else
    raw_n=$((raw_n + 1))
    head -c 2097152 "$f" >"$hdr" 2>>"$pyerr" || scan_err=1
  fi
  name=$(hdr_field 'general.name' "$hdr")
  arch=$(hdr_field 'general.architecture' "$hdr")
  tensors=$(hdr_field '# tensors declared' "$hdr")
  qwen=$(LC_ALL=C rg -a -o -i -N --no-filename --no-unicode \
    'qwen[0-9][A-Za-z0-9._-]{0,48}' "$hdr" 2>/dev/null | sort -u | head -n 6 | tr '\n' ' ')
  printf '   parser: %s' "$mode"
  [ -n "$name" ] && printf '  name: %s' "$name"
  [ -n "$arch" ] && printf '  arch: %s' "$arch"
  [ -n "$tensors" ] && printf '  tensors: %s (not scanned)' "$tensors"
  printf '  qwen-like: %s\n' "${qwen:-none}"
  if [ "$mode" = "raw" ]; then
    printf '   metadata parse failed; first 2MB only'
    if [ -s "$pyerr" ]; then
      printf ' (%s)' "$(head -n 1 "$pyerr")"
    fi
    printf '\n'
  fi
  scan_header_text "$hdr"
}

SEARCH_TARGETS=()
DIRECT_WEIGHTS=()
MAX_BYTES=$(size_to_bytes "$MAX_FILESIZE") || die "--max-filesize must look like 10, 512K, 1M, or 1G"
for t in "${TARGETS[@]}"; do
  if [ -f "$t" ]; then
    case "$(kind_of "$t")" in
      header) DIRECT_WEIGHTS+=("$t"); continue ;;
      skip)
        printf 'skipping tensor file (no header parser): %s\n' "$t"
        continue
        ;;
    esac
    if [ -n "$SELF" ] && [ "$(basename -- "$t")" = "$SELF" ]; then
      printf 'skipping this scanner: %s\n' "$t"
      continue
    fi
    bytes=$(file_bytes "$t" || true)
    if [ -n "${bytes:-}" ] && [ "$bytes" -gt "$MAX_BYTES" ]; then
      printf 'skipping %s (%s bytes, over %s)\n' "$t" "$bytes" "$MAX_FILESIZE"
      continue
    fi
  fi
  SEARCH_TARGETS+=("$t")
done

follow_word=off
[ "$FOLLOW" -eq 1 ] && follow_word=on
printf 'Limits: hidden and gitignored files are searched; directory symlinks %s; text over %s skipped; %s matches per file per pass; tensor bytes not scanned.\n' \
  "$follow_word" "$MAX_FILESIZE" "$MAX_COUNT"
printf 'Targets:\n'
for t in "${TARGETS[@]}"; do
  printf '  %s\n' "$t"
done
printf '\n'

if [ "${#SEARCH_TARGETS[@]}" -gt 0 ]; then
  run_pass "Pass 1: high-confidence incident strings" high "${HIGH_PARTS[@]}"
  run_pass "Pass 2: broad indicators (review the file, do not assume)" broad "${BROAD_PARTS[@]}"
  run_pass "Pass 3: unshare + private tmpfs shape (review; same line only)" shape "${SHAPE_PARTS[@]}"
else
  printf '(no text targets; model files are checked below)\n\n'
fi

printf '== Pass 4: GGUF / safetensors metadata (not tensor bytes) ==\n'
list=$tmpdir/models.list
: >"$list"
if [ "${#SEARCH_TARGETS[@]}" -gt 0 ]; then
  errf=$tmpdir/files.err
  file_args=(--files --hidden --no-ignore --glob-case-insensitive
    -g '*.gguf' -g '*.safetensors'
    -g '!**/.git/**' -g '!**/node_modules/**'
    -g '!**/.qwen-iocs.*/**')
  [ "$FOLLOW" -eq 1 ] && file_args+=(-L)
  LC_ALL=C rg "${file_args[@]}" -- "${SEARCH_TARGETS[@]}" >"$list" 2>"$errf"
  ec=$?
  note_rg_err "$errf" "$ec"
  if [ "$ec" -ge 2 ] && [ ! -s "$list" ]; then
    printf '(model file list failed)\n'
  fi
fi
if [ "${#DIRECT_WEIGHTS[@]}" -gt 0 ]; then
  printf '%s\n' "${DIRECT_WEIGHTS[@]}" >>"$list"
fi
if [ -s "$list" ]; then
  sort -u "$list" -o "$list"
  filtered=$tmpdir/models.filtered
  : >"$filtered"
  while IFS= read -r f || [ -n "$f" ]; do
    [ -n "$f" ] || continue
    # rg --files ignores globs for a path you passed explicitly, so a text
    # file would otherwise be parsed as if it were a weight.
    [ "$(kind_of "$f")" = header ] || continue
    printf '%s\n' "$f"
  done <"$list" >"$filtered"
  mv "$filtered" "$list"
fi
if [ -s "$list" ]; then
  while IFS= read -r f || [ -n "$f" ]; do
    [ -n "$f" ] || continue
    scan_one_model "$f"
    printf '\n'
  done <"$list"
else
  printf '(no .gguf or .safetensors under targets)\n'
fi
printf '\n'

if [ "$scan_err" -eq 1 ]; then
  printf 'Scan did not cover every file (see rg errors above). Do not read a miss as a clean result.\n'
fi
if [ "$raw_n" -gt 0 ]; then
  printf 'Metadata parser missed %s model file(s); those were prefix-scanned only.\n' "$raw_n"
fi

if [ "$high_n" -gt 0 ]; then
  printf 'RESULT (exit 1): high-confidence incident string(s) found: %s.\n' "$high_n"
  printf 'Open each path. A saved article, a renamed copy of this script, or a blocker plugin is not a callback.\n'
  exit 1
fi
if [ "$broad_n" -gt 0 ] || [ "$shape_n" -gt 0 ]; then
  printf 'RESULT (exit %s): no high-confidence strings. Broad hits: %s. Command-shape hits: %s.\n' \
    "$([ "$STRICT" -eq 1 ] && printf 1 || printf 3)" "$broad_n" "$shape_n"
  printf 'These show up in normal Aliyun configs, cloud docs, and rootless-container scripts. Read the path.\n'
  if [ "$STRICT" -eq 1 ]; then
    exit 1
  fi
  if [ "$scan_err" -eq 1 ]; then
    exit 2
  fi
  exit 3
fi
if [ "$scan_err" -eq 1 ]; then
  printf 'RESULT (exit 2): no indicator strings in the part that was scanned, but the walk failed.\n'
  exit 2
fi
printf 'RESULT (exit 0): no indicator strings in the scanned text or model metadata.\n'
printf 'This does not clear the weights. Text over %s was not opened. Logs you deleted are not here either.\n' \
  "$MAX_FILESIZE"
exit 0
