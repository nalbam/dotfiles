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

# vscode
[[ "$TERM_PROGRAM" == "vscode" ]] && . "$(code --locate-shell-integration-path bash)"

# kiro
[[ "$TERM_PROGRAM" == "kiro" ]] && . "$(kiro --locate-shell-integration-path zsh)"

# Amazon Q post block. Keep at the bottom of this file.
[[ -f "${HOME}/Library/Application Support/amazon-q/shell/zshrc.post.zsh" ]] && builtin source "${HOME}/Library/Application Support/amazon-q/shell/zshrc.post.zsh"
