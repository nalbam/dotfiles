# zshrc

export ZSH="$HOME/.oh-my-zsh"

ZSH_THEME="robbyrussell"
ZSH_THEME="dracula"

ZSH_DISABLE_COMPFIX="true"

plugins=(git kube-ps1)

source $ZSH/oh-my-zsh.sh

# User configuration

OS_ARCH="$(uname -m)"

if [ -f ~/.aliases ]; then
  source ~/.aliases
fi

export PATH="$HOME/.local/bin${PATH+:$PATH}"

if [ -d "/opt/homebrew/bin" ]; then
  export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"
fi

if [ -d "/opt/homebrew/opt/gnu-getopt/bin" ]; then
  export PATH="/opt/homebrew/opt/gnu-getopt/bin:$PATH"
elif [ -d "/usr/local/opt/gnu-getopt/bin" ]; then
  export PATH="/usr/local/opt/gnu-getopt/bin:$PATH"
fi

PS1='$(kube_ps1)'$PS1

[[ $commands[kubectl] ]] && source <(kubectl completion zsh)

if [ -d "/opt/homebrew/share/zsh-autosuggestions" ]; then
  source /opt/homebrew/share/zsh-autosuggestions/zsh-autosuggestions.zsh
elif [ -d "/usr/local/share/zsh-autosuggestions" ]; then
  source /usr/local/share/zsh-autosuggestions/zsh-autosuggestions.zsh
fi

if [ -d "/opt/homebrew/share/zsh-syntax-highlighting" ]; then
  source /opt/homebrew/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
elif [ -d "/usr/local/share/zsh-syntax-highlighting" ]; then
  source /usr/local/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
fi

# gopath
if [ -d "$HOME/go" ]; then
  export GOPATH="$HOME/go"
  export PATH="$GOPATH/bin:$PATH"
fi

# pyenv
if [ -d "$HOME/.pyenv" ]; then
  export PYENV_ROOT="$HOME/.pyenv"
  [[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
  eval "$(pyenv init -)"
fi

# tfenv
export TFENV_AUTO_INSTALL=true
if [[ "${OS_ARCH}" == "arm64" ]]; then
  export TFENV_ARCH=arm64
fi
if [ -d "$HOME/.tfenv" ]; then
  export TFENV_ROOT="$HOME/.tfenv"
  export PATH="$TFENV_ROOT/bin:$PATH"
fi
