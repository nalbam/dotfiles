# Homebrew setup (if installed)
if [ -x /opt/homebrew/bin/brew ]; then
  eval "$(/opt/homebrew/bin/brew shellenv)"
fi

# Pyenv setup (if installed)
if command -v pyenv >/dev/null 2>&1; then
  eval "$(pyenv init --path)"
fi
