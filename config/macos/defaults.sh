#!/usr/bin/env bash

# Based on Mathias Bynens' ~/.macos — https://mths.be/macos
# Preference consumers checked on macOS 26.6; app overrides may take precedence.

# Let the installer record completion only when all settings succeed.
set -e

# Close System Settings so it cannot overwrite pending preference changes.
osascript -e 'tell application id "com.apple.systempreferences" to quit'

###############################################################################
# Sound                                                                       #
###############################################################################

# Mute the startup chime using the current Sound settings NVRAM key.
# https://support.apple.com/102230
# Only this setting needs sudo; avoid authentication when already muted.
if ! STARTUP_MUTE=$(nvram StartupMute 2>/dev/null) || [[ "$STARTUP_MUTE" != $'StartupMute\t%01' ]]; then
  sudo nvram StartupMute=%01
fi

###############################################################################
# Keyboard and text input                                                     #
###############################################################################

# Repeat held keys instead of opening the accent selection menu.
defaults write -g ApplePressAndHoldEnabled -bool false
# Use a fast repeat rate and a short delay before repeating.
defaults write NSGlobalDomain KeyRepeat -int 2
defaults write NSGlobalDomain InitialKeyRepeat -int 15

# Disable substitutions that alter source code in Cocoa text fields.
defaults write NSGlobalDomain NSAutomaticCapitalizationEnabled -bool false
defaults write NSGlobalDomain NSAutomaticDashSubstitutionEnabled -bool false
defaults write NSGlobalDomain NSAutomaticQuoteSubstitutionEnabled -bool false
defaults write NSGlobalDomain NSAutomaticSpellingCorrectionEnabled -bool false

# Keep double-space period insertion enabled.
defaults write NSGlobalDomain NSAutomaticPeriodSubstitutionEnabled -bool true

###############################################################################
# Windows and screenshots                                                     #
###############################################################################

# Speed up animated frame resizing in apps using NSWindow's default timing.
# https://developer.apple.com/documentation/appkit/nswindow/animationresizetime(_:)
defaults write NSGlobalDomain NSWindowResizeTime -float 0.001

# Save screenshots to the clipboard.
defaults write com.apple.screencapture target -string "clipboard"

###############################################################################
# Finder and file storage                                                     #
###############################################################################

# Prefer list view, visible filename extensions, and folders first by name.
# Existing per-folder view settings can override the default view style.
defaults write com.apple.finder FXPreferredViewStyle -string "Nlsv"
defaults write NSGlobalDomain AppleShowAllExtensions -bool true
defaults write com.apple.finder _FXSortFoldersFirst -bool true

# Show the folder path, item counts, and available disk space.
defaults write com.apple.finder ShowPathbar -bool true
defaults write com.apple.finder ShowStatusBar -bool true

# Search the current folder and disable Finder window animations.
defaults write com.apple.finder FXDefaultSearchScope -string "SCcf"
defaults write com.apple.finder DisableAllAnimations -bool true

# Disable confirmation when changing extensions or emptying the Trash.
defaults write com.apple.finder FXEnableExtensionChangeWarning -bool false
defaults write com.apple.finder WarnOnEmptyTrash -bool false

# Skip .DS_Store files on network volumes; existing files are not removed.
# https://support.apple.com/102064
defaults write com.apple.desktopservices DSDontWriteNetworkStores -bool true

# Browse all interfaces for network sharing discovery through sharingd.
defaults write com.apple.NetworkBrowser BrowseAllInterfaces -bool true

# Show the user's Library folder.
chflags nohidden ~/Library

# Do not offer newly connected disks as Time Machine backup destinations.
defaults write com.apple.TimeMachine DoNotOfferNewDisksForBackup -bool true

###############################################################################
# Dock and hot corners                                                        #
###############################################################################

defaults write com.apple.dock mouse-over-hilite-stack -bool true
defaults write com.apple.dock tilesize -int 36
# Used when Dock magnification is enabled in the user's settings.
defaults write com.apple.dock largesize -int 60
defaults write com.apple.dock mineffect -string "genie"
defaults write com.apple.dock minimize-to-application -bool true

# Three corners prevent the screen saver; bottom-right locks the screen.
defaults write com.apple.dock wvous-tl-corner -int 6
defaults write com.apple.dock wvous-tr-corner -int 6
defaults write com.apple.dock wvous-bl-corner -int 6
defaults write com.apple.dock wvous-br-corner -int 13

###############################################################################
# Terminal applications                                                       #
###############################################################################

# Use UTF-8 in Terminal and disable iTerm2's quit confirmation.
defaults write com.apple.Terminal StringEncodings -array 4
defaults write com.googlecode.iterm2 PromptOnQuit -bool false

###############################################################################
# Activity Monitor                                                            #
###############################################################################

# Open the main window, show all processes sorted by CPU, and use a CPU meter.
defaults write com.apple.ActivityMonitor OpenMainWindow -bool true
defaults write com.apple.ActivityMonitor ShowCategory -int 0
defaults write com.apple.ActivityMonitor SortColumn -string "CPUUsage"
defaults write com.apple.ActivityMonitor SortDirection -int 0
defaults write com.apple.ActivityMonitor IconType -int 5

###############################################################################
# Screen lock                                                                 #
###############################################################################

# Ordinary com.apple.screensaver defaults do not configure the effective lock
# delay on current macOS. sysadminctl authenticates with the login password;
# '-' prompts without exposing it in command arguments or logs.
SCREEN_LOCK_STATUS=$(sysadminctl -screenLock status 2>&1)
if [[ "$SCREEN_LOCK_STATUS" != *"screenLock delay is immediate"* ]]; then
  # curl | bash leaves stdin connected to the installer pipe. sysadminctl
  # needs terminal input to prompt instead of consuming that pipe as a password.
  if ! { exec 3</dev/tty; } 2>/dev/null; then
    echo "Immediate screen lock requires a terminal for authentication. Re-run from Terminal, or set the password delay to Immediately in System Settings > Lock Screen." >&2
    exit 1
  fi
  echo "Setting immediate screen lock; enter your macOS login password when prompted."
  sysadminctl -screenLock immediate -password - <&3
  exec 3<&-
  SCREEN_LOCK_STATUS=$(sysadminctl -screenLock status 2>&1)
  if [[ "$SCREEN_LOCK_STATUS" != *"screenLock delay is immediate"* ]]; then
    echo "Failed to verify immediate screen lock." >&2
    exit 1
  fi
fi

# Keep the desktop and terminal alive so the installer can record success.
echo "Done. After installation completes, log out or restart to apply pending UI changes."
