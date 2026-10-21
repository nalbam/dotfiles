# Shared Bash/Zsh startup; sourcing this file never installs Node.js.
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"

if [ -d "$NVM_DIR" ]; then
  if ! command -v nvm >/dev/null 2>&1; then
    for _dotfiles_nvm_script in \
      "$NVM_DIR/nvm.sh" \
      "${BREWPATH:-/usr/local}/opt/nvm/nvm.sh" \
      "/opt/homebrew/opt/nvm/nvm.sh" \
      "/home/linuxbrew/.linuxbrew/opt/nvm/nvm.sh"; do
      if [ -s "$_dotfiles_nvm_script" ]; then
        # Restore the inherited selection before nvm auto-use inspects PATH.
        if [ -n "${NVM_BIN:-}" ] && [ -x "$NVM_BIN/node" ]; then
          case "${PATH:-}" in
            "$NVM_BIN" | "$NVM_BIN":*) ;;
            *) export PATH="$NVM_BIN${PATH:+:$PATH}" ;;
          esac
        fi
        . "$_dotfiles_nvm_script"
        for _dotfiles_nvm_completion in \
          "${_dotfiles_nvm_script%/*}/bash_completion" \
          "${_dotfiles_nvm_script%/*}/etc/bash_completion.d/nvm" \
          "${BREWPATH:-/usr/local}/opt/nvm/etc/bash_completion.d/nvm" \
          "/opt/homebrew/opt/nvm/etc/bash_completion.d/nvm" \
          "/home/linuxbrew/.linuxbrew/opt/nvm/etc/bash_completion.d/nvm"; do
          if [ -s "$_dotfiles_nvm_completion" ]; then
            . "$_dotfiles_nvm_completion"
            break
          fi
        done
        break
      fi
    done
  fi

  # nvm can replace an inherited entry without moving it ahead of Homebrew.
  if command -v nvm >/dev/null 2>&1 && [ -n "${NVM_BIN:-}" ] && [ -x "$NVM_BIN/node" ]; then
    case "${PATH:-}" in
      "$NVM_BIN" | "$NVM_BIN":*) ;;
      *) export PATH="$NVM_BIN${PATH:+:$PATH}" ;;
    esac
  fi
fi

unset _dotfiles_nvm_script _dotfiles_nvm_completion
