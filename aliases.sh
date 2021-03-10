alias t='toaster'
alias tu='t update'
alias tt='t tools'

c() {
    toaster cdw ${1}
    if [ -f /tmp/toaster-temp-result ]; then
        cd $(cat /tmp/toaster-temp-result)
    fi
}

ibrew() {
  arch --x86_64 /usr/local/bin/brew $@
}

alias e='toaster env'
alias n='toaster git'
alias s='toaster ssh'
alias r='toaster region'
alias x='toaster ctx'
alias v='toaster vsc'

alias a='aws'
alias k='kubectl'
alias h='helm'

alias av='aws-vault'

alias tf='terraform'
alias tfe='tfenv'
alias tfc='rm -rf .terraform && tf init'
alias tfp='tfc && tf plan'
alias tfa='tfc && tf apply'
alias tfd='tfc && tf destroy'
alias tff='tf init && tf fmt'
alias tfg='tf init && tf graph'
alias tfo='tf init && tf output'

alias tfdoc="terraform-docs markdown"

alias py='python'
alias py3='python3'

alias dt='date -u +"%Y-%m-%dT%H:%M:%SZ"'

# alias p='reveal-md -w --port 8888 --theme https://raw.githubusercontent.com/nalbam/docs/master/.theme/black.css'
alias p='reveal-md -w --port 8888 --theme night'

alias chrome="/Applications/Google\\ \\Chrome.app/Contents/MacOS/Google\\ \\Chrome"

# export GOPATH=$HOME/work
# export PATH=$PATH:$GOPATH/bin
