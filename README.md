# CodeGate

Give people on your network their **own private workspace** on your Mac, in
their browser: **VS Code** (editor, terminal, Python, Jupyter, Node) or a
**full Ubuntu desktop**. Nothing to install on their side. Each person gets
their own container, their own copy of the files you prepared, and their own
login name in the terminal. Their changes stay in their copy, and they can
download all of it as a zip.

You open a **room**, share its **PIN**, and people join with a name.

- **Two room types**, each with its own PIN: VS Code, or the real Ubuntu 24.04
  desktop (GNOME Shell with the Ubuntu Dock, in the browser, with Terminal, Files,
  Firefox, VS Code, Python and Jupyter). It runs without systemd by giving GNOME a private
  system bus with mocked login/power services, and renders in software.
- **Starter files.** Point it at a folder and every member gets their own copy
  the first time they open their workspace. **Reset** restores the original.
- **Yours to manage** from [Dromac](https://github.com/yatharth1011/dromac)'s
  dashboard: open/close rooms, see who's active, stop or remove anyone, set how
  many run at once, switch internet access on or off, and save any member's (or
  everyone's) work as a zip into `~/Documents/CodeGate Collected`.
- **Isolated by default**, see [What it protects](#what-it-protects).

## Set up

```bash
brew install colima docker     # the container runtime
./install.sh                   # installs CodeGate into ~/Library/Application Support/CodeGate
python3 "$HOME/Library/Application Support/CodeGate/server.py"
```

Dromac's dashboard can start it for you (the `$ codegate` card). Then, in
Dromac: **manage, build image** (once per room type; the first build downloads a
few GB), **+ add from folder...** for starter files, and **open room** to get a
PIN.

## How people use it

1. You open a room and share its PIN.
2. They go to `https://<your-mac-ip>:8901/`, enter a name and the PIN, and are
   shown a **resume code**: the only way to get the same workspace back from
   another browser or device.
3. They open their workspace (or one starter), edit and run things, and press
   **Download** for a zip of their work.

**Trust the certificate once per device:** open `http://<your-mac-ip>:8902/`
and follow the steps. Without it the browser warns every time, and VS Code's
notebooks and previews won't load (they need a trusted HTTPS origin). Typing
`http://` on port 8901 is redirected to `https://`.

## What it protects

Running other people's code on your Mac is the risky part, so it's built to
contain them:

- **Off by default and owner-only.** Rooms are opened only from your Mac: the
  admin API answers loopback clients that send a custom header, so a web page
  can't trigger it. Dromac warns you before opening a room.
- **Joining needs a PIN** (8 characters, expires after 12 hours, one per room
  type) and a name; returning members need their resume code. Wrong attempts
  are throttled per device, and there's a cap on new joins per hour.
- **One container per member**, running as an unprivileged user with **no Linux
  capabilities and `no-new-privileges`**, hard **CPU, memory, process and disk
  limits** (VS Code: 1 CPU / 1 GB / 256 processes / 2 GB disk; the desktop gets
  more), an init process so runaway processes can't wedge it, and no Docker
  socket. Idle workspaces are removed after 30 minutes; their files persist.
- **They can't reach your Mac.** The container VM has no access to your files
  (Colima's default home-folder mount is removed), and a firewall in the VM
  drops all traffic from member containers to private and local networks: your
  Mac and its services, your LAN, the VM itself, and other members. They can
  still reach the internet (you can switch that off), because installing
  packages needs it.
- **HTTPS only** (TLS 1.2+) with a certificate from a local CA whose name
  constraints only allow private addresses. Sessions are random `Secure` /
  `HttpOnly` cookies; each session is routed only to its own member's
  container. Gate pages refuse framing and check `Host` and `Origin`.
- **It stops by itself.** The HTTPS gate is live only while a room is open (it
  comes back by itself if the server restarts with a room still open).

### Limits to know about

- Members can use your internet connection. Turn internet off in Dromac's
  manager if that's a problem, or only open rooms for people you know.
- The container VM is capped at 4 CPUs / 8 GB by default (`colima start --cpu
  --memory` to change); the per-room "at once" limit keeps you inside it.
- Isolation is container-grade, not a hardware boundary. A kernel-level
  container escape would land in the small Linux VM, not on macOS, but treat
  rooms as "people I'd let use a shared lab machine".

## Layout

| File | What it does |
|---|---|
| `server.py` | Admin API (loopback + header), the certificate/info page on port 8902, starts the gate |
| `gate.py` | The HTTPS front door on port 8901: join, portal, download, and per-member proxying |
| `spaces.py` | Rooms, PINs, members, starter files, Docker containers, the firewall, quotas |
| `docker/code`, `docker/desktop` | The two workspace images |

It's plain Python 3 (standard library only) plus `openssl` for the local CA.

## License

MIT. See [LICENSE](LICENSE).
