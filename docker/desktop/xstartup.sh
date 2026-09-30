#!/bin/bash
# Runs as the member: virtual display + a real Ubuntu (GNOME Shell) session + the noVNC web server on 6080.
# /tmp is a noexec tmpfs, so everything here is run through bash.
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/runtime-$USER}"
mkdir -p "$XDG_RUNTIME_DIR" "$HOME/.vnc" && chmod 700 "$XDG_RUNTIME_DIR"

# The X server listens on localhost only and the container publishes just 6080;
# CodeGate's gate is the only way in, so VNC itself needs no password.
Xtigervnc :1 -geometry 1600x900 -depth 24 -localhost yes -SecurityTypes None -AlwaysShared \
  -rfbport 5901 +extension GLX >"$HOME/.vnc/xserver.log" 2>&1 &
for i in $(seq 1 50); do [ -e /tmp/.X11-unix/X1 ] && break; sleep 0.2; done

export DISPLAY=:1 XDG_SESSION_TYPE=x11 XDG_CURRENT_DESKTOP=ubuntu:GNOME XDG_SESSION_DESKTOP=ubuntu \
  GNOME_SHELL_SESSION_MODE=ubuntu LIBGL_ALWAYS_SOFTWARE=1 \
  XDG_DATA_DIRS=/usr/share/ubuntu:/usr/local/share:/usr/share XDG_CONFIG_DIRS=/etc/xdg/xdg-ubuntu:/etc/xdg
( bash /opt/codegate/gnome-session.sh >"$HOME/.vnc/gnome.log" 2>&1 & )

exec websockify --web /usr/share/novnc 6080 localhost:5901
