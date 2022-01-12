# zshrc

export ZSH="$HOME/.oh-my-zsh"

ZSH_THEME="robbyrussell"

ZSH_DISABLE_COMPFIX="true"

plugins=(git)

source $ZSH/oh-my-zsh.sh

# User configuration

if [ -f ~/.aliases ]; then
  source ~/.aliases
fi

export PATH="$HOME/.local/bin${PATH+:$PATH}"

PATH_BREW="$(echo $PATH | grep '/opt/homebrew/bin' | wc -l  | xargs)"
if [ "x${PATH_BREW}" == "x0" ]; then
  export PATH="/opt/homebrew/bin:/opt/homebrew/sbin${PATH+:$PATH}";
fi

if [ -d "/opt/homebrew/opt/gnu-getopt/bin" ]; then
  export PATH="/opt/homebrew/opt/gnu-getopt/bin:$PATH"
elif [ -d "/usr/local/opt/gnu-getopt/bin" ]; then
  export PATH="/usr/local/opt/gnu-getopt/bin:$PATH"
fi

if [ -d "/opt/homebrew/opt/kube-ps1" ]; then
  source "/opt/homebrew/opt/kube-ps1/share/kube-ps1.sh"
  PS1='$(kube_ps1)'$PS1
elif [ -d "/usr/local/opt/kube-ps1" ]; then
  source "/usr/local/opt/kube-ps1/share/kube-ps1.sh"
  PS1='$(kube_ps1)'$PS1
fi

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
