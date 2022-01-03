#!/bin/bash

OS_NAME="$(uname | awk '{print tolower($0)}')"
OS_ARCH="$(uname -m)"

if [ "${OS_NAME}" == "darwin" ]; then
  INSTALLER="brew"
fi

################################################################################

command -v tput > /dev/null && TPUT=true

_echo() {
  if [ "${TPUT}" != "" ] && [ "$2" != "" ]; then
    echo -e "$(tput setaf $2)$1$(tput sgr0)"
  else
    echo -e "$1"
  fi
}

_read() {
  if [ "${TPUT}" != "" ]; then
    printf "$(tput setaf 6)$1$(tput sgr0)"
  else
    printf "$1"
  fi
  read ANSWER
}

_result() {
  _echo "# $@" 4
}

_command() {
  _echo "$ $@" 3
}

_success() {
  _echo "+ $@" 2
  exit 0
}

_error() {
  _echo "- $@" 1
  exit 1
}

_git_config() {
  DEFAULT="$(whoami)"
  _read "Please input git user name [${DEFAULT}]: "

  GIT_USERNAME="${ANSWER:-${DEFAULT}}"
  git config --global user.name "${GIT_USERNAME}"

  DEFAULT="${GIT_USERNAME}@nalbam.com"
  _read "Please input git user email [${DEFAULT}]: "

  GIT_USEREMAIL="${ANSWER:-${DEFAULT}}"
  git config --global user.email "${GIT_USEREMAIL}"

  git config --global core.autocrlf input
  git config --global core.pager ''
  git config --global core.precomposeunicode true
  git config --global core.quotepath false
  git config --global pull.ff only

  _command "git config --list"
  git config --list
}

_install_brew() {
  INSTALLED=
  command -v $1 > /dev/null || INSTALLED=false
  if [ ! -z ${INSTALLED} ]; then
    _command "brew install ${2:-$1}"
    brew install ${2:-$1}
  fi
}

_install_brew_path() {
  INSTALLED=$(cat /tmp/brew_list | grep "$1" | wc -l | xargs)

  if [ "x${INSTALLED}" == "x0" ]; then
    _command "brew install ${2:-$1}"
    brew install ${2:-$1}
  fi
}

_install_brew_apps() {
  INSTALLED=$(ls /Applications/ | grep "$1" | wc -l | xargs)

  if [ "x${INSTALLED}" == "x0" ]; then
    _command "brew install -cask ${2:-$1}"
    brew install -cask ${2:-$1}
  fi
}

_install_npm() {
  INSTALLED=
  command -v $1 > /dev/null || INSTALLED=false
  if [ ! -z ${INSTALLED} ]; then
    _command "npm install -g ${2:-$1}"
    npm install -g ${2:-$1}
  fi
}

_install_npm_path() {
  if [ -d /usr/local/lib/node_modules/ ]; then
    INSTALLED=$(ls /usr/local/lib/node_modules/ | grep "$1" | wc -l | xargs)
  else
    INSTALLED=
  fi

  if [ "x${INSTALLED}" == "x0" ]; then
    _command "npm install -g ${2:-$1}"
    npm install -g ${2:-$1}
  fi
}

################################################################################

_result "${OS_NAME} ${OS_ARCH} [${INSTALLER}]"

if [ "${INSTALLER}" == "" ]; then
  _error "Not supported OS."
fi

mkdir -p ~/.aws
mkdir -p ~/.ssh

# ssh keygen
[ ! -f ~/.ssh/id_rsa ] && ssh-keygen -q -t ed25519 -f ~/.ssh/id_ed25519 -N ''

# ssh config
if [ ! -f ~/.ssh/config ]; then
  curl -sL -o ~/.ssh/config https://raw.githubusercontent.com/nalbam/dotfiles/main/.ssh/config
  chmod 400 ~/.ssh/config
fi

# aws config
if [ ! -f ~/.aws/config ]; then
  curl -sL -o ~/.aws/config https://raw.githubusercontent.com/nalbam/dotfiles/main/.aws/config
  chmod 400 ~/.aws/config
fi

curl -sL -o ~/.aliases https://raw.githubusercontent.com/nalbam/dotfiles/main/.aliases
curl -sL -o ~/.bashrc https://raw.githubusercontent.com/nalbam/dotfiles/main/.bashrc
curl -sL -o ~/.vimrc https://raw.githubusercontent.com/nalbam/dotfiles/main/.vimrc
curl -sL -o ~/.zprofile https://raw.githubusercontent.com/nalbam/dotfiles/main/.zprofile
curl -sL -o ~/.zshrc https://raw.githubusercontent.com/nalbam/dotfiles/main/.zshrc

# git config
GIT_USERNAME="$(git config --global user.name)"
if [ -z ${GIT_USERNAME} ]; then
  _git_config
fi

# brew for mac
if [ "${INSTALLER}" == "brew" ]; then
  # brew
  command -v brew > /dev/null || HAS_BREW=false
  if [ ! -z ${HAS_BREW} ]; then
    _command "xcode-select --install"
    sudo xcodebuild -license
    xcode-select --install
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  fi

  _command "brew update..."
  brew update

  _command "brew upgrade..."
  brew upgrade

  brew list > /tmp/brew_list

  # zsh
  command -v zsh > /dev/null || HAS_ZSH=false
  if [ ! -z ${HAS_ZSH} ]; then
    _command "brew install zsh"
    brew install zsh
    chsh -s /bin/zsh
    /bin/bash -c "$(curl -fsSL https://raw.github.com/robbyrussell/oh-my-zsh/master/tools/install.sh)"
  fi

  # getopt
  GETOPT=$(getopt 2>&1 | head -1 | xargs)
  if [ "${GETOPT}" == "--" ]; then
    _command "brew install gnu-getopt"
    brew install gnu-getopt
    brew link --force gnu-getopt
  fi

  _command "check utils..."

  _install_brew_path bat
  _install_brew_path fzf
  _install_brew_path git
  _install_brew_path go
  _install_brew_path jq
  _install_brew_path telnet
  _install_brew_path tmux
  _install_brew_path wget
  _install_brew_path yq
  _install_brew_path figlet
  _install_brew_path grpcurl
  _install_brew_path httpie

  _install_brew_path jenv
  _install_brew_path pyenv
  _install_brew_path tfenv

  _install_brew_path argo
  _install_brew_path argocd
  _install_brew_path aws-vault
  _install_brew_path awscli
  _install_brew_path eksctl
  _install_brew_path gh
  _install_brew_path helm
  _install_brew_path helm-docs
  _install_brew_path hub
  _install_brew_path hugo
  _install_brew_path istioctl
  _install_brew_path jsonnet
  _install_brew_path k6
  _install_brew_path k9s
  _install_brew_path kubectx
  _install_brew_path kubernetes-cli
  _install_brew_path minikube
  _install_brew_path tanka
  _install_brew_path terraform-docs

  _install_brew_path kubectl-argo-rollouts argoproj/tap/kubectl-argo-rollouts

  _install_brew_path kube-ps1
  _install_brew_path zsh-syntax-highlighting

  if [ "${OS_ARCH}" == "x86_64" ]; then
    _install_brew_path qemu
    _install_brew_path podman
  elif [ "${OS_ARCH}" == "arm64" ]; then
    _install_brew_path podman-apple-silicon simnalamburt/x/podman-apple-silicon
  fi

  # nodejs
  _install_brew_path node
  _install_npm_path reveal-md

  # java
  _install_brew_path openjdk
  _install_brew_path maven

  # apps
  _install_brew_path dropbox
  _install_brew_path google-chrome
  _install_brew_path istat-menus
  _install_brew_path iterm2
  _install_brew_path slack
  _install_brew_path visual-studio-code

  # _install_brew_apps "Dropbox.app" dropbox
  # _install_brew_apps "Google Chrome.app" google-chrome
  # _install_brew_apps "iTerm.app" iterm2
  # _install_brew_apps "Visual Studio Code.app" visual-studio-code

  # _install_brew_apps "iStat Menus.app" istat-menus
  # _install_brew_apps "Slack.app" slack # app store

  _command "check versions..."
  _result "awscli:  $(aws --version | cut -d' ' -f1 | cut -d'/' -f2)"
  _result "kubectl: $(kubectl version --client -o json | jq .clientVersion.gitVersion -r)"
  _result "helm:    $(helm version --client --short | cut -d'+' -f1)"
  _result "argocd:  $(argocd version --client -o json | jq .client.Version -r | cut -d'+' -f1)"

  _command "brew cleanup..."
  brew cleanup
fi

_success
