if [ -d "$HOME/.local/bin" ]; then
  PATH="$HOME/.local/bin:${PATH+:$PATH}"
fi

if [ -d "/opt/homebrew/bin" ]; then
  export PATH="/opt/homebrew/bin:${PATH+:$PATH}"
fi
if [ -d "/opt/homebrew/sbin" ]; then
  export PATH="/opt/homebrew/sbin:${PATH+:$PATH}"
fi
if [ -d "/home/linuxbrew/.linuxbrew/bin" ]; then
  export PATH="/home/linuxbrew/.linuxbrew/bin:${PATH+:$PATH}"
fi

if [ -f ~/.aliases ]; then
  source ~/.aliases
fi
