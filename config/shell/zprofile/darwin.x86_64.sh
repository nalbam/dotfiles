# Homebrew setup (if installed)
if command -v brew >/dev/null 2>&1; then
  eval "$(brew shellenv)"
fi

# Pyenv setup (if installed)
if command -v pyenv >/dev/null 2>&1; then
  eval "$(pyenv init --path)"
fi
