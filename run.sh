#!/bin/bash

OS_NAME="$(uname | awk '{print tolower($0)}')"
OS_FULL="$(uname -a)"

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
      command -v brew > /dev/null || ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
  fi
}

_update() {
  # update
  echo "================================================================================"
  echo "update..."

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

      command -v argo > /dev/null || brew install argo
      command -v argocd > /dev/null || brew install argocd
      command -v aws > /dev/null || brew install awscli
      command -v fzf > /dev/null || brew install fzf
      command -v gh > /dev/null || brew install gh
      command -v git > /dev/null || brew install git
      command -v go > /dev/null || brew install go
      command -v helm > /dev/null || brew install helm
      command -v http > /dev/null || brew install httpie
      command -v istioctl > /dev/null || brew install istioctl
      command -v jenv > /dev/null || brew install jenv
      command -v jq > /dev/null || brew install jq
      command -v jsonnet > /dev/null || brew install jsonnet
      command -v k9s > /dev/null || brew install k9s
      command -v kubectl > /dev/null || brew install kubernetes-cli
      command -v node > /dev/null || brew install node
      command -v pyenv > /dev/null || brew install pyenv
      command -v telnet > /dev/null || brew install telnet
      command -v telnet > /dev/null || brew install telnet
      command -v tfenv > /dev/null || brew install tfenv
      command -v tmux > /dev/null || brew install tmux
      command -v wget > /dev/null || brew install wget
      command -v yq > /dev/null || brew install yq
      command -v zsh > /dev/null || brew install zsh

      command -v java > /dev/null || HAS_JAVA=false
      if [ ! -z ${HAS_JAVA} ]; then
          brew tap AdoptOpenJDK/openjdk
          brew install --cask adoptopenjdk8
      fi
      command -v mvn > /dev/null || brew install maven

      brew cleanup
  fi
}

################################################################################

_prepare

_update
