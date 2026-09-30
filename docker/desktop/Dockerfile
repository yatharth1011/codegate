# CodeGate desktop workspace: the real Ubuntu 24.04 desktop (GNOME Shell + Ubuntu Dock), served to the browser with
# noVNC. Like the VS Code image, the entrypoint runs as root only long enough
# to create the member's Unix user, then drops to that user with no
# capabilities and no-new-privileges.
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8

RUN echo 'Acquire::Retries "8";' > /etc/apt/apt.conf.d/80-retries \
    && apt-get update && apt-get install -y --no-install-recommends \
      dbus-x11 x11-xserver-utils xdg-utils \
      tigervnc-standalone-server tigervnc-common novnc websockify \
      fonts-dejavu fonts-noto-core fonts-jetbrains-mono adwaita-icon-theme yaru-theme-icon yaru-theme-gtk \
      python3 python3-pip python3-venv python3-dev python3-numpy python3-pandas python3-matplotlib \
      python3-scipy python3-ipykernel python3-tk git curl wget unzip zip nano vim less procps \
      build-essential nodejs npm ca-certificates gnupg software-properties-common \
    && rm -rf /var/lib/apt/lists/* && ln -sf /usr/bin/python3 /usr/local/bin/python

# Firefox from Mozilla's PPA (Ubuntu's own package is a snap, which can't run in a container).
RUN add-apt-repository -y ppa:mozillateam/ppa \
    && printf 'Package: *\nPin: release o=LP-PPA-mozillateam\nPin-Priority: 1001\n' > /etc/apt/preferences.d/mozilla-firefox \
    && apt-get update && apt-get install -y --no-install-recommends firefox \
    && rm -rf /var/lib/apt/lists/*

# The actual Ubuntu session. There is no systemd in a container, so startup gives GNOME a
# private system bus with mocked login1/upower/polkit services (python3-dbusmock); rendering
# is software (llvmpipe).
RUN apt-get update && apt-get install -y --no-install-recommends \
      gnome-shell gnome-session gnome-session-bin gnome-settings-daemon gnome-terminal nautilus gedit \
      gnome-shell-extension-ubuntu-dock gnome-shell-extension-appindicator gnome-backgrounds \
      yaru-theme-gnome-shell yaru-theme-sound ubuntu-session ubuntu-settings gnome-control-center \
      mesa-utils libgl1-mesa-dri dconf-cli gsettings-desktop-schemas at-spi2-core \
      fonts-ubuntu ubuntu-wallpapers-noble python3-dbusmock \
    && rm -rf /var/lib/apt/lists/*

# VS Code (Microsoft's tarball; the .deb is unusable here). --no-sandbox because the container has no
# capabilities to give Chromium's sandbox; the container itself is the sandbox.
RUN set -e; case "$(dpkg --print-architecture)" in arm64) A=arm64;; *) A=x64;; esac; \
    curl -fL --retry 8 --retry-all-errors --connect-timeout 20 "https://update.code.visualstudio.com/latest/linux-$A/stable" -o /tmp/code.tgz \
    && mkdir -p /opt/vscode && tar xzf /tmp/code.tgz -C /opt/vscode --strip-components=1 && rm /tmp/code.tgz \
    && printf '#!/bin/sh\nexec /opt/vscode/bin/code --no-sandbox --password-store=basic "$@"\n' > /usr/local/bin/code && chmod 755 /usr/local/bin/code \
    && printf '[Desktop Entry]\nName=Visual Studio Code\nComment=Code Editing. Redefined.\nExec=/usr/local/bin/code %%F\nIcon=/opt/vscode/resources/app/resources/linux/code.png\nType=Application\nCategories=Development;IDE;TextEditor;\nStartupWMClass=Code\nMimeType=text/plain;inode/directory;\n' > /usr/share/applications/code.desktop

# Firefox's own content sandbox needs kernel features the locked-down container (no capabilities)
# deliberately lacks; the container itself is the sandbox.
ENV MOZ_DISABLE_CONTENT_SANDBOX=1 MOZ_DISABLE_GMP_SANDBOX=1

COPY entrypoint.sh /opt/codegate/entrypoint.sh
COPY xstartup.sh gnome-session.sh gnome-init.sh /opt/codegate/
RUN chmod 755 /opt/codegate/*.sh

WORKDIR /
ENTRYPOINT ["/opt/codegate/entrypoint.sh"]
