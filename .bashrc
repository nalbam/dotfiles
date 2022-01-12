export PATH="$HOME/.local/bin${PATH+:$PATH}"

PATH_BREW="$(echo $PATH | grep '/opt/homebrew/bin' | wc -l  | xargs)"
if [ "x${PATH_BREW}" == "x0" ]; then
  export PATH="/opt/homebrew/bin:/opt/homebrew/sbin${PATH+:$PATH}";
fi

if [ -f ~/.aliases ]; then
  source ~/.aliases
fi
