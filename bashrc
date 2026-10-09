# locale: unset or invalid (e.g. Termius sets en_KR.UTF-8) falls back to ASCII and breaks unicode prompts
if [ "$(locale charmap 2>/dev/null)" != "UTF-8" ]; then
  export LANG="en_US.UTF-8"
fi

if [ -d "$HOME/.local/bin" ]; then
  PATH="$HOME/.local/bin${PATH:+:$PATH}"
fi

if [ -d "/opt/homebrew/bin" ]; then
  export PATH="/opt/homebrew/bin${PATH:+:$PATH}"
fi
if [ -d "/opt/homebrew/sbin" ]; then
  export PATH="/opt/homebrew/sbin${PATH:+:$PATH}"
fi
if [ -d "/home/linuxbrew/.linuxbrew/bin" ]; then
  export PATH="/home/linuxbrew/.linuxbrew/bin${PATH:+:$PATH}"
fi

if [ -f ~/.aliases ]; then
  source ~/.aliases
fi

# Optional editor shell integration.
case "$TERM_PROGRAM" in
  vscode) _editor_cli=code ;;
  kiro) _editor_cli=kiro ;;
  *) _editor_cli= ;;
esac
if [ -n "$_editor_cli" ] && command -v "$_editor_cli" >/dev/null 2>&1; then
  if _editor_integration=$("$_editor_cli" --locate-shell-integration-path bash) && [ -r "$_editor_integration" ]; then
    . "$_editor_integration"
  fi
fi
unset _editor_cli _editor_integration
