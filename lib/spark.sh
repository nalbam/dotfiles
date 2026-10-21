# shellcheck shell=bash
# Shared by the DGX Spark modules (llm, monitoring, vibemon).
#
# stacks/dgx-spark is copied into a runtime directory where Docker Compose runs
# it. Runtime-only files (.env, credentials, backups, generated targets) exist
# only there and are never overwritten. The directory name is also the Compose
# project name, so it must stay stable to keep the running containers.

DOT_SPARK_DIR="${DOT_SPARK_DIR:-$HOME/.config/dgx-spark}"
DOT_SPARK_SOURCE="$DOT_HOME/stacks/dgx-spark"

spark_supported() { dot_platform_is dgx-spark; }

# Managed files, relative to the stack root, one per line.
spark_files() {
  (
    cd "$DOT_SPARK_SOURCE" || exit 1
    find . -type f \
      ! -name .env ! -name '.env.grafana' ! -name 'model-targets.json' \
      ! -name '*.pyc' ! -name '*.pyo' ! -name .DS_Store \
      ! -path './backups/*' ! -path './bench/*' ! -path '*/__pycache__/*' | LC_ALL=C sort
  )
}

# Managed files limited to PREFIX... (all files when no prefix is given).
spark_scope() {
  local file prefix
  spark_files | while IFS= read -r file; do
    [ $# -gt 0 ] || { printf '%s\n' "$file"; continue; }
    for prefix in "$@"; do
      case "$file" in
        "./$prefix"*) printf '%s\n' "$file"; break ;;
      esac
    done
  done
}

# Digest of the managed files under ROOT (source or runtime), optionally
# limited to PREFIX...; a missing file changes the digest.
spark_digest() {
  local root="$1" file list
  shift
  list=$(mktemp "${TMPDIR:-/tmp}/dot-spark.XXXXXX") || return 1
  spark_scope "$@" | while IFS= read -r file; do
    if [ -f "$root/$file" ]; then
      printf '%s %s\n' "$(dot_md5 "$root/$file")" "$file"
    else
      printf 'missing %s\n' "$file"
    fi
  done > "$list"
  dot_md5 "$list"
  rm -f "$list"
}

spark_sync() {
  local file
  mkdir -p "$DOT_SPARK_DIR" || return 1
  spark_files | while IFS= read -r file; do
    mkdir -p "$DOT_SPARK_DIR/${file%/*}" &&
      cp -p "$DOT_SPARK_SOURCE/$file" "$DOT_SPARK_DIR/$file.dot-tmp" &&
      mv -f "$DOT_SPARK_DIR/$file.dot-tmp" "$DOT_SPARK_DIR/$file" || exit 1
  done
}

# True when the runtime copy of the files (limited to PREFIX...) matches the repository.
spark_in_sync() {
  [ "$(spark_digest "$DOT_SPARK_SOURCE" "$@")" = "$(spark_digest "$DOT_SPARK_DIR" "$@")" ]
}

# spark_mark KEY [PREFIX...]: record that KEY was applied with the current
# source content of its files.
spark_mark() {
  local key="$1"
  shift
  spark_digest "$DOT_SPARK_SOURCE" "$@" | dot_write "$DOT_STATE/applied/spark-$key"
}

spark_marked() {
  local key="$1"
  shift
  [ "$(cat "$DOT_STATE/applied/spark-$key" 2>/dev/null)" = "$(spark_digest "$DOT_SPARK_SOURCE" "$@")" ]
}

# Runs a stack script from the runtime directory.
spark_script() {
  local script="$1"
  shift
  (cd "$DOT_SPARK_DIR" && "scripts/$script" "$@")
}

spark_mode() {
  sed -n 's/^SPARK_MODE=//p' "$DOT_SPARK_DIR/.env" 2>/dev/null | tail -1
}
