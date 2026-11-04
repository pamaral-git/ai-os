#!/usr/bin/env bash
# llama-openshell.sh — start llama-swap ONLY if the OpenShell (rootless Podman) sandbox is up
# and verifiably locked down.
#
#   IMAGE=<image> ./llama-openshell.sh setup     one-time: create the sandbox
#   ./llama-openshell.sh up [-- <llama-swap cmd>] every day: verify, then exec llama-swap
#                                                 (no command given = the default below)
#   ./llama-openshell.sh sbx <cmd...>             run a command INSIDE the sandbox
#
# Fail closed: any failed check => exit 1 and llama-swap never starts. After llama-swap is
# listening, the sandbox is probed again; a leak or an unusable check stops llama-swap.
#
# Uses `sandbox create` flags --detach and --approval-mode (present in 0.1.2); --restart-policy is
# only used if your build lists it in `openshell sandbox create --help`.
# On macOS, upgrade OpenShell by re-running its official install script, not `brew upgrade`.
# EXPERIMENTAL: not yet verified against a real gateway. Run `setup` once and read the
# effective policy it prints before trusting this.
#
# Environment overrides (all optional):
#   SANDBOX, POLICY, HOST_IP, LLAMA_PORT, GATEWAY_PORT, LLAMA_SWAP_CONFIG
set -euo pipefail

SANDBOX="${SANDBOX:-llama-work}"
POLICY="${POLICY:-$HOME/.config/openshell/policy.yaml}"
# Podman Machine's host-gateway address; must equal the endpoint host in policy.yaml.
HOST_IP="${HOST_IP:-192.168.127.254}"
LLAMA_PORT="${LLAMA_PORT:-9008}"          # must equal the endpoint port in policy.yaml
GATEWAY_PORT="${GATEWAY_PORT:-17670}"
LLAMA_SWAP_CONFIG="${LLAMA_SWAP_CONFIG:-$HOME/models/llama-swap.yaml}"
LLAMA_URL="http://${HOST_IP}:${LLAMA_PORT}"
DEFAULT_LLAMA_CMD=(llama-swap -config "$LLAMA_SWAP_CONFIG" -listen "127.0.0.1:${LLAMA_PORT}")
CURL=/usr/bin/curl                         # the client the policy allows; the image must have it

die() { echo "REFUSING TO START: $*" >&2; exit 1; }
sbx_exec() { openshell sandbox exec -n "$SANDBOX" --no-login-shell --timeout 30 -- "$@"; }

[[ "$HOST_IP" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]] || die "HOST_IP '$HOST_IP' is not an IPv4 address"
[[ "$LLAMA_PORT" =~ ^[0-9]{1,5}$ ]] || die "LLAMA_PORT '$LLAMA_PORT' is not a number"
[[ "$GATEWAY_PORT" =~ ^[0-9]{1,5}$ ]] || die "GATEWAY_PORT '$GATEWAY_PORT' is not a number"

# Prints the HTTP status the sandbox's allowed curl gets for a URL.
#   "000" = connection failed/denied;  "ERR" = the sandbox could not run curl at all
# (so a broken sandbox can never look like a passing denial test).
# Usage: http_code URL [extra curl args...]
http_code() {
  local url="$1"; shift
  local out
  out="$(sbx_exec "$CURL" -sS -m 6 "$@" -o /dev/null -w '%{http_code}' "$url" 2>/dev/null)" || true
  out="${out//[$'\n\r ']/}"
  [[ "$out" =~ ^[0-9]{3}$ ]] || out="ERR"
  printf '%s' "$out"
}

ensure_podman() {
  command -v podman >/dev/null || die "podman not installed (brew install podman)"
  podman info >/dev/null 2>&1 || { echo "starting podman machine..." >&2; podman machine start >&2 || die "podman machine won't start"; }
  [ "$(podman info --format '{{.Host.Security.Rootless}}' 2>/dev/null)" = "true" ] \
    || die "Podman is not rootless. Do not use a rootful machine."
}

ensure_gateway() {
  command -v openshell >/dev/null || die "openshell CLI not found"
  openshell status >/dev/null 2>&1 || {
    echo "gateway down; restarting service..." >&2
    brew services restart openshell >/dev/null 2>&1 || true
    local i; for i in $(seq 1 30); do openshell status >/dev/null 2>&1 && break; sleep 1; done
    openshell status >/dev/null 2>&1 || die "OpenShell gateway not reachable"
  }
  # Capture first, then grep: `cmd | grep -q` under `set -o pipefail` fails when grep exits early
  # and cmd gets SIGPIPE. Also retry, because right after a restart the driver can take a few
  # seconds to be listed.
  local info="" j
  for j in $(seq 1 15); do
    info="$(openshell gateway info 2>/dev/null || true)"
    grep -qi podman <<<"$info" && break
    sleep 1
  done
  grep -qi podman <<<"$info" || die "gateway is not using the Podman driver (check gateway.toml). 'openshell gateway info' printed: ${info:-<nothing>}"
  # Gateway must be loopback only; a leftover OPENSHELL_BIND_ADDRESS=0.0.0.0 overrides gateway.toml.
  local l; l="$(lsof -nP -iTCP:"${GATEWAY_PORT}" -sTCP:LISTEN 2>/dev/null || true)"
  [ -n "$l" ] || die "nothing listening on :${GATEWAY_PORT}"
  if grep -Eq "(\*|0\.0\.0\.0|\[::\]):${GATEWAY_PORT}" <<<"$l"; then
    die "gateway listens on all interfaces. Remove OPENSHELL_BIND_ADDRESS from gateway.env and restart."
  fi
}

# The sandbox policy must name exactly HOST_IP and LLAMA_PORT (not a longer IP/port containing them).
check_policy_mentions_endpoint() {
  local pol ip_re="${HOST_IP//./\\.}"
  pol="$(openshell policy get "$SANDBOX" --full 2>/dev/null)" || die "could not read the sandbox policy"
  grep -Eq "(^|[^0-9.])${ip_re}([^0-9.]|\$)" <<<"$pol" \
    || die "sandbox policy does not mention host $HOST_IP; recreate the sandbox with the current policy.yaml"
  grep -Eq "(^|[^0-9])${LLAMA_PORT}([^0-9]|\$)" <<<"$pol" \
    || die "sandbox policy does not mention port $LLAMA_PORT; recreate the sandbox with the current policy.yaml"
}

# Landlock is best_effort in policy.yaml, so prove it is actually enforced: /var/tmp is writable by
# ordinary permissions but NOT listed in the policy, so a successful write means Landlock is off.
check_fs_enforcement() {
  if ! sbx_exec test -d /var/tmp >/dev/null 2>&1 || ! sbx_exec test -w /var/tmp >/dev/null 2>&1; then
    echo "note: /var/tmp absent or not writable in the image; filesystem enforcement test inconclusive" >&2
    return 0
  fi
  if sbx_exec touch /var/tmp/.fs-probe >/dev/null 2>&1; then
    sbx_exec rm -f /var/tmp/.fs-probe >/dev/null 2>&1 || true
    die "sandbox could write to /var/tmp, which policy.yaml does not allow; Landlock is NOT enforced."
  fi
}

cmd_setup() {
  [ -n "${IMAGE:-}" ] || die "set IMAGE=<agent image in Podman's store, with $CURL and a WORKDIR other than />"
  [ -f "$POLICY" ] || die "policy not found: $POLICY"
  ensure_podman; ensure_gateway
  # --restart-policy does not exist in OpenShell 0.1.2; only pass it where this build supports it.
  local create_args=(--name "$SANDBOX" --from "$IMAGE" --policy "$POLICY"
                     --no-auto-providers --approval-mode manual --detach)
  if openshell sandbox create --help 2>&1 | grep -q -- '--restart-policy'; then
    create_args+=(--restart-policy always)
  else
    echo "note: this OpenShell has no --restart-policy; the sandbox won't auto-restart ('up' restarts it on demand)." >&2
  fi
  openshell sandbox create "${create_args[@]}" -- sleep infinity
  echo "Effective policy (the only network endpoint must be ${HOST_IP}:${LLAMA_PORT}):"
  openshell policy get "$SANDBOX" --full
  echo "Setup done. Now: $0 up"
}

cmd_up() {
  [ "${1:-}" = "--" ] && shift
  local llama_cmd=("${DEFAULT_LLAMA_CMD[@]}")
  if [ "$#" -gt 0 ]; then llama_cmd=("$@"); fi

  ensure_podman
  ensure_gateway

  sbx_exec true >/dev/null 2>&1 || {
    echo "sandbox not ready; trying to start it..." >&2
    openshell sandbox start "$SANDBOX" >/dev/null 2>&1 || die "sandbox '$SANDBOX' missing or won't start (run: IMAGE=... $0 setup)"
    sbx_exec true >/dev/null 2>&1 || die "sandbox '$SANDBOX' not executable after start"
  }
  sbx_exec test -x "$CURL" >/dev/null 2>&1 || die "no $CURL in the sandbox image; the self-test needs the client your policy allows"
  check_policy_mentions_endpoint
  check_fs_enforcement

  # Negative tests with the ALLOWED binary (curl): a hostile model could use exactly this client,
  # so denial must come from the network policy, not from a binary mismatch.
  local u code
  for u in "https://example.com" "http://1.1.1.1" "http://169.254.169.254/" "http://100.100.100.200/"; do
    code="$(http_code "$u")"
    case "$code" in
      ERR) die "sandbox could not run curl; the egress denial tests would be meaningless." ;;
      2*|3*) die "sandbox curl reached $u (HTTP $code). Egress is NOT locked down." ;;
    esac
  done
  if sbx_exec test -x /usr/bin/unshare >/dev/null 2>&1; then
    if sbx_exec /usr/bin/unshare -Urm true >/dev/null 2>&1; then
      die "'unshare -Urm' succeeded inside the sandbox; user-namespace escape path is open."
    fi
  else
    echo "note: no unshare in image, namespace test skipped" >&2
  fi
  echo "sandbox '$SANDBOX': rootless Podman, loopback gateway, policy endpoint matches, filesystem enforced, external egress denied, unshare -Urm denied."

  # After llama-swap is listening: positive control (/health must work), then L7 probes.
  # Any failure (including an unusable check) kills llama-swap: fail closed.
  local parent=$$
  (
    stop_llama() { echo "[sandbox check] FAIL: $1 Stopping llama-swap." >&2; kill -TERM "$parent" 2>/dev/null || true; exit 0; }
    probe() { # probe PATH [curl args...]: must NOT succeed
      local path="$1"; shift
      local c; c="$(http_code "${LLAMA_URL}${path}" "$@")"
      case "$c" in
        ERR)   stop_llama "probe of ${path} could not run." ;;
        2*|3*) stop_llama "unlisted request ${path} $* got HTTP $c; L7 rules not enforced." ;;
      esac
    }
    ok=0
    for i in $(seq 1 90); do
      kill -0 "$parent" 2>/dev/null || exit 0          # llama-swap already gone
      [ "$(http_code "$LLAMA_URL/health")" = "200" ] && { ok=1; break; }
      sleep 1
    done
    [ "$ok" -eq 1 ] || stop_llama "sandbox could not GET $LLAMA_URL/health (policy IP, binary path, or llama-swap down?)."
    echo "[sandbox check] sandbox reaches llama-swap at $LLAMA_URL (allowed path works)." >&2

    probe /running                                   # route not in the policy
    probe //running                                  # double-slash variant
    probe /health/../running --path-as-is            # dot-segment traversal
    probe /health/%2e%2e/running --path-as-is        # encoded traversal
    probe /upstream/probe/props                      # llama-swap's raw upstream passthrough
    probe /health -X POST                            # method not allowed on an allowed path
    echo "[sandbox check] unlisted routes, traversal variants and wrong methods are denied (L7 enforced)." >&2
  ) &

  exec "${llama_cmd[@]}"
}

case "${1:-}" in
  setup) cmd_setup ;;
  up)    shift; cmd_up "$@" ;;
  sbx)   shift; openshell sandbox exec -n "$SANDBOX" --tty -- "$@" ;;
  *)     echo "usage: $0 {setup | up [-- <llama-swap cmd...>] | sbx <cmd...>}" >&2; exit 2 ;;
esac
