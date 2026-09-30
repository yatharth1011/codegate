#!/bin/bash
# Inside the session bus: first-run settings, the member's work folder, then the shell itself.
if [ ! -e "$HOME/.config/codegate-ubuntu-2" ]; then
  gsettings set org.gnome.shell favorite-apps "['firefox.desktop','org.gnome.Nautilus.desktop','org.gnome.Terminal.desktop','code.desktop','org.gnome.gedit.desktop','org.gnome.Settings.desktop']"
  gsettings set org.gnome.desktop.screensaver lock-enabled false
  gsettings set org.gnome.desktop.session idle-delay 0
  gsettings set org.gnome.desktop.screensaver idle-activation-enabled false
  gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type nothing
  mkdir -p "$HOME/.config"; touch "$HOME/.config/codegate-ubuntu-2"
fi
/usr/libexec/gsd-xsettings &
( sleep 12; nautilus "$CG_FOLDER" >/dev/null 2>&1 & ) &
exec gnome-shell --x11
