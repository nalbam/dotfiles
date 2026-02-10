#!/bin/bash

# tmux welcome message with usage guide

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
RESET='\033[0m'

# Clear screen
clear

# Banner with figlet if available
if command -v figlet &> /dev/null; then
  echo -e "${CYAN}"
  figlet -f standard "tmux"
  echo -e "${RESET}"
else
  echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${RESET}"
  echo -e "${CYAN}║                            TMUX                                ║${RESET}"
  echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${RESET}"
fi

# Session info
echo -e "${GREEN}Session: ${YELLOW}main${RESET}"
echo -e "${GREEN}Host: ${YELLOW}$(hostname)${RESET}"
echo -e "${GREEN}Date: ${YELLOW}$(date '+%Y-%m-%d %H:%M:%S')${RESET}"
echo ""

# Usage guide
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${MAGENTA}                      TMUX QUICK REFERENCE${RESET}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo -e "${YELLOW}Basic Commands:${RESET}"
echo -e "  ${GREEN}Ctrl-b c${RESET}       Create new window"
echo -e "  ${GREEN}Ctrl-b ,${RESET}       Rename current window"
echo -e "  ${GREEN}Ctrl-b n${RESET}       Next window"
echo -e "  ${GREEN}Ctrl-b p${RESET}       Previous window"
echo -e "  ${GREEN}Ctrl-b 0-9${RESET}     Switch to window number"
echo ""
echo -e "${YELLOW}Pane Management:${RESET}"
echo -e "  ${GREEN}Ctrl-b |${RESET}       Split vertically"
echo -e "  ${GREEN}Ctrl-b -${RESET}       Split horizontally"
echo -e "  ${GREEN}Ctrl-b h/j/k/l${RESET} Navigate panes (Vim-style)"
echo -e "  ${GREEN}Ctrl-b x${RESET}       Close current pane"
echo ""
echo -e "${YELLOW}Session Control:${RESET}"
echo -e "  ${GREEN}Ctrl-b d${RESET}       Detach session (keeps running)"
echo -e "  ${GREEN}Ctrl-b r${RESET}       Reload tmux config"
echo -e "  ${GREEN}tmux ls${RESET}        List sessions"
echo -e "  ${GREEN}tmux attach${RESET}    Attach to session"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
