#!/bin/bash
# A private system bus with just enough of login1/upower/polkit mocked for GNOME Shell to start.
cat > "$XDG_RUNTIME_DIR/system.conf" <<CONF
<busconfig><type>system</type><listen>unix:path=$XDG_RUNTIME_DIR/system_bus_socket</listen>
<auth>EXTERNAL</auth><policy context="default"><allow send_destination="*" eavesdrop="true"/><allow eavesdrop="true"/><allow own="*"/></policy></busconfig>
CONF
dbus-daemon --config-file="$XDG_RUNTIME_DIR/system.conf" --fork
export DBUS_SYSTEM_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/system_bus_socket"
for t in logind upower polkitd; do python3 -m dbusmock --system -t $t >/dev/null 2>&1 & done
sleep 2
exec dbus-run-session -- bash /opt/codegate/gnome-init.sh
