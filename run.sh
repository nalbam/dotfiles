#!/usr/bin/env bash

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

_result() {
  _echo "# $@" 4
}

_success() {
  _echo "+ $@" 2
  exit 0
}

_error() {
  _echo "- $@" 1
  exit 1
}

_prepare() {
  echo "================================================================================"
  echo "${OS_NAME} [${INSTALLER}]"

  if [ "${INSTALLER}" == "" ]; then
    _error "Not supported OS."
  fi

  mkdir -p ~/.aws
  mkdir -p ~/.ssh

  # ssh keygen
  [ ! -f ~/.ssh/id_rsa ] && ssh-keygen -q -f ~/.ssh/id_rsa -N ''

  # ssh config
  if [ ! -f ~/.ssh/config ]; then
cat <<EOF > ~/.ssh/config
Host *
    StrictHostKeyChecking no
EOF
  fi
  chmod 400 ~/.ssh/config

  # brew for mac
  if [ "${INSTALLER}" == "brew" ]; then
    command -v brew > /dev/null || HAS_BREW=false

    if [ ! -z ${HAS_BREW} ]; then
      sudo xcodebuild -license
      xcode-select --install

      /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi

    if [ "${OS_ARCH}" == "arm64" ]; then
      command -v ibrew > /dev/null || HAS_IBREW=false

      if [ ! -z ${HAS_IBREW} ]; then
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
      fi
    fi
  fi
}

_install_brew() {
  command -v $1 > /dev/null || brew install ${2:-$1}
}

_install_brew_apps() {
  INSTALLED=$(ls /Applications | grep $1 | wc -l | xargs)

  if [ "x${INSTALLED}" == "x0" ]; then
    brew install -cask ${2:-$1}
  fi
}

_install() {
  echo "================================================================================"

  if [ "${INSTALLER}" == "brew" ]; then
      brew update && brew upgrade

      # cat Brewfile| grep 'brew ' | cut -d'"' -f2 | while read APP; do
      #   command -v ${APP} > /dev/null || brew install ${APP}
      # done

      # getopt
      GETOPT=$(getopt 2>&1 | head -1 | xargs)
      if [ "${GETOPT}" == "--" ]; then
        brew install gnu-getopt
        brew link --force gnu-getopt
      fi

      _install_brew argocd
      _install_brew aws awscli
      _install_brew fzf
      _install_brew gh
      _install_brew git
      _install_brew go
      _install_brew grpcurl
      _install_brew http httpie
      _install_brew jenv
      _install_brew jq
      _install_brew jsonnet
      _install_brew node
      _install_brew pyenv
      _install_brew telnet
      _install_brew terraform-docs
      _install_brew tmux
      _install_brew wget
      _install_brew yq
      _install_brew zsh
      # _install_brew ffmpeg
      # _install_brew youtube-dl

      _install_brew tfenv
      _install_brew helm

      _install_brew kubectl kubernetes-cli
      _install_brew istioctl
      _install_brew k9s

      command -v java > /dev/null || HAS_JAVA=false
      if [ ! -z ${HAS_JAVA} ]; then
        brew tap AdoptOpenJDK/openjdk
        brew install --cask adoptopenjdk8
      fi

      _install_brew mvn maven

      _install_brew_apps "Dropbox.app" dropbox
      _install_brew_apps "Google Chrome.app" google-chrome
      _install_brew_apps "iStat Menus.app" istat-menus
      _install_brew_apps "iTerm.app" iterm2
      # _install_brew_apps "Slack.app" slack # app store
      _install_brew_apps "Visual Studio Code.app" visual-studio-code

      brew cleanup
  fi
}

_aliases() {
  TARGET=${HOME}/${1}

  ALIASES="${HOME}/.aliases"

  curl -sL -o ${ALIASES} nalbam.github.io/dotfiles/aliases.sh

  if [ -f "${ALIASES}" ]; then
    touch ${TARGET}
    HAS_ALIAS="$(cat ${TARGET} | grep '.aliases' | wc -l | xargs)"

    if [ "x${HAS_ALIAS}" == "x0" ]; then
      echo "" >> ${TARGET}
      echo "if [ -f ~/.aliases ]; then" >> ${TARGET}
      echo "  source ~/.aliases" >> ${TARGET}
      echo "fi" >> ${TARGET}
      echo "" >> ${TARGET}
      echo "if [ -d /opt/homebrew/bin ]; then" >> ${TARGET}
      echo "  export PATH=\"/opt/homebrew/bin:$PATH\"" >> ${TARGET}
      echo "fi" >> ${TARGET}
    fi

    source ${ALIASES}
  fi
}

################################################################################

_prepare

_install

_aliases ".bashrc"
_aliases ".zshrc"
