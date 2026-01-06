# Homebrew setup (if installed)
if [ -x /home/linuxbrew/.linuxbrew/bin/brew ]; then
  eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
fi

# Pyenv setup (if installed)
if command -v pyenv >/dev/null 2>&1; then
  eval "$(pyenv init --path)"
fi
