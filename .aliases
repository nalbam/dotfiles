#!/bin/bash

alias t='toaster'
alias tu='t update'
alias tt='t tools'

c() {
    toaster cdw ${1}
    if [ -f /tmp/toaster-temp-result ]; then
        cd $(cat /tmp/toaster-temp-result)
    fi
}

alias e='toaster env'
alias n='toaster git'
alias q='toaster assume'
alias r='toaster region'
alias s='toaster ssh'
alias v='toaster vsc'
alias x='toaster ctx'
alias z='toaster ns'

alias a='aws'
alias k='kubectl'
alias h='helm'

alias am='aws sts get-caller-identity | jq .'

alias av='aws-vault'
alias ave='export AWS_VAULT= && av exec'
alias ava='export AWS_VAULT= && av exec daangn/alpha --'
alias avp='export AWS_VAULT= && av exec daangn/prod --'
alias avn='export AWS_VAULT= && av exec nalbam --'

alias tf='terraform'
alias tfc='rm -rf .terraform && rm -rf .terraform.lock.hcl'
alias tfi='tf init'
alias tff='tf init && tf fmt'
alias tfp='tf init && tf fmt && tf plan'
alias tfa='tf init && tf fmt && tf apply'
alias tfd='tf init && tf destroy'
alias tfs='tf init && tf state'
alias tfg='tf init && tf graph'
alias tfo='tf init && tf output'

alias tfim='tf init && tf import'

alias tfsl='tf init && tf state list'
alias tfss='tf init && tf state show'
alias tfsr='tf init && tf state rm'

alias tfdoc="terraform-docs markdown"

alias docker='podman'

alias py='python'
alias py3='python3'

alias dt='date -u +"%Y-%m-%dT%H:%M:%SZ"'

# alias p='reveal-md -w --port 8888 --theme https://raw.githubusercontent.com/nalbam/docs/master/.theme/black.css'
alias p='reveal-md -w --port 8888 --theme night'

# export GOPATH=$HOME/work
# export PATH=$PATH:$GOPATH/bin
