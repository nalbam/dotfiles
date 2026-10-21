# shellcheck shell=bash
# Module registry, profiles and runner.
#
# A module is modules/<name>.sh and defines these functions:
#   <name>::describe   one-line description                      (required)
#   <name>::up         install when missing, upgrade when due     (required, idempotent)
#   <name>::supported  return 0 when the module works here        (optional, default: yes)
#   <name>::detect     return 0 when already installed            (optional, enables adoption)
#   <name>::status     print a one-line state                     (optional)
#   <name>::cli        handle `dot <name> ARGS...`                (optional)
#
# profiles/<platform> lists the modules a platform runs by default. Add-ons are
# kept in $DOT_CONFIG/modules: `name` enables a module, `-name` disables one
# (including a profile module) and prevents adoption.

# Execution order. Every module must appear here exactly once.
DOT_MODULE_ORDER="base apt server git brew macos node python claude shell terminal nvim ai docker k3s llm monitoring vibemon"

dot_fn() { declare -F "$1" >/dev/null 2>&1; }

dot_in_list() {
  local item="$1" entry
  shift
  for entry in "$@"; do
    [ "$entry" = "$item" ] && return 0
  done
  return 1
}

dot_module_load() {
  case "$1" in
    '' | *[!a-z0-9]*) return 1 ;;
  esac
  dot_fn "$1::up" && return 0
  [ -f "$DOT_HOME/modules/$1.sh" ] || return 1
  # shellcheck disable=SC1090
  . "$DOT_HOME/modules/$1.sh" && dot_fn "$1::up" && dot_fn "$1::describe"
}

dot_module_supported() {
  dot_module_load "$1" || return 1
  if dot_fn "$1::supported"; then "$1::supported"; fi
}

_dot_words() {
  [ -f "$1" ] || return 0
  sed 's/#.*//' "$1" | tr -s ' \t' '\n\n' | grep -v '^$'
}

dot_profile_modules() { _dot_words "$DOT_HOME/profiles/$DOT_PLATFORM"; }
dot_addons_enabled() { _dot_words "$DOT_CONFIG/modules" | grep -v '^-'; }
dot_addons_disabled() { _dot_words "$DOT_CONFIG/modules" | sed -n 's/^-//p'; }

# dot_addon_set NAME enable|disable|reset
dot_addon_set() {
  local name="$1" state="$2" current
  current=$(_dot_words "$DOT_CONFIG/modules" | grep -vx -e "$name" -e "-$name")
  {
    [ -z "$current" ] || printf '%s\n' "$current"
    case "$state" in
      enable) printf '%s\n' "$name" ;;
      disable) printf -- '-%s\n' "$name" ;;
    esac
  } | dot_write "$DOT_CONFIG/modules"
}

# Prints the modules to run, in execution order: profile modules and enabled
# add-ons, minus explicitly disabled modules.
dot_selected_modules() {
  local wanted disabled name
  wanted="$(dot_profile_modules; dot_addons_enabled)"
  disabled="$(dot_addons_disabled)"
  for name in $DOT_MODULE_ORDER; do
    # shellcheck disable=SC2086
    dot_in_list "$name" $wanted || continue
    # shellcheck disable=SC2086
    dot_in_list "$name" $disabled && continue
    printf '%s\n' "$name"
  done
}

# Enable supported add-ons that are already installed on this machine, so a
# host configured before dot (or by hand) is kept up to date.
dot_adopt_modules() {
  local selected disabled name
  selected="$(dot_selected_modules)"
  disabled="$(dot_addons_disabled)"
  for name in $DOT_MODULE_ORDER; do
    # shellcheck disable=SC2086
    dot_in_list "$name" $selected $disabled && continue
    dot_module_supported "$name" || continue
    dot_fn "$name::detect" || continue
    if "$name::detect"; then
      dot_addon_set "$name" enable
      dot_info "Adopted existing installation: $name"
    fi
  done
}

# Runs one module in a subshell so a failure or exit stays inside that module.
dot_module_run() {
  local name="$1"
  dot_module_load "$name" || { dot_warn "Unknown module: $name"; return 1; }
  if ! dot_module_supported "$name"; then
    dot_skip "$name is not supported on $DOT_PLATFORM"
    return 0
  fi
  (
    dot_load_paths
    "$name::up"
  )
}

# Serialize runs that change the machine. The lock is a symlink whose target
# is the owner's pid, created atomically together with its content. A lock
# whose owner no longer exists is renamed aside (atomic) and taken again.
dot_lock() {
  local lock="$DOT_STATE/lock" owner attempt=0
  mkdir -p "$DOT_STATE" || return 1
  until ln -s "$$" "$lock" 2>/dev/null; do
    owner=$(readlink "$lock" 2>/dev/null)
    if [ -n "$owner" ] && kill -0 "$owner" 2>/dev/null; then
      dot_echo "  ✗ Another dot run is active (pid $owner). If that process is not dot, remove $lock." 1 >&2
      return 1
    fi
    attempt=$((attempt + 1))
    [ "$attempt" -le 3 ] || return 1
    mv "$lock" "$lock.stale.$$" 2>/dev/null && rm -f "$lock.stale.$$"
  done
  DOT_LOCKED="$lock"
}

dot_unlock() {
  if [ -n "${DOT_LOCKED:-}" ] && [ "$(readlink "$DOT_LOCKED" 2>/dev/null)" = "$$" ]; then
    rm -f "$DOT_LOCKED"
  fi
  DOT_LOCKED=""
}
