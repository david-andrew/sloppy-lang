# A matchmaking server of your own

With a matchmaking server, a game's Invite a friend shows a short room code ("KX7P4") and a link
with it, the same each time on that computer; friends type the code into Join a friend, or open
the link, and are in. Without one, players pass an invite code and a reply code back and forth
(lib/invite.jo, [Playing together over a network](MULTIPLAYER.md)).

The server, `tools/rendezvous.jo`, only passes those two codes between the games in a room. The
games then connect straight to each other (WebRTC), as they do with codes: no game traffic goes
through it. Where two players' networks allow no straight path (some mobile data, schools,
offices), a TURN relay passes their packets; coturn on the same machine does that, and the
server gives each game a password for it that works for a day.

This page sets up all three on one small DigitalOcean droplet: the server, Caddy in front of it
(web pages served over https may only reach `wss://`, so Caddy adds TLS, with a free Let's
Encrypt certificate), and coturn. Below, `match.example.org` stands for the name you choose and
`203.0.113.7` for the droplet's address.

| Port | For |
|---|---|
| 443/tcp (and 80/tcp) | web pages: `wss://match.example.org` (Caddy, to the server); 80 for Let's Encrypt |
| 7700/tcp | native programs: `ws://match.example.org:7700` (the server itself: a native program has no TLS) |
| 3478/udp and tcp, 49160-49460/udp | TURN (coturn) |

Cost: the $6 a month droplet (1 GB memory, 1 TB of traffic a month) has plenty of room; the $4
one (512 MB, 500 GB) works too. Relayed games are small (a rollback game sends inputs: tens of MB
an hour for a player relayed). The name is a subdomain of a domain you have: no extra cost.

## 1. The droplet

DigitalOcean, Create, Droplets:
- Region: the one nearest most players.
- Image: Ubuntu 24.04 (LTS) x64.
- Size: Basic, Regular SSD, $6/mo (or $4/mo).
- Authentication: SSH key (add yours). Hostname: `match`.

Create it and note its IPv4 address. Then, from your computer:

```sh
ssh root@203.0.113.7
apt update && apt upgrade -y
ufw allow OpenSSH
ufw allow 80,443/tcp
ufw allow 7700/tcp
ufw allow 3478
ufw allow 49160:49460/udp
ufw enable
ufw status          # the rules above, "Status: active"
```

On the $4 droplet (512 MB), add some swap, so that `apt upgrade` has room:

```sh
fallocate -l 1G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo "/swapfile none swap sw 0 0" >> /etc/fstab
```

(DigitalOcean's Cloud Firewall, under Networking, does the same from the dashboard; one of the two
is enough.)

## 2. The name

Where your domain's DNS is (your registrar, or DigitalOcean's Networking, Domains), add an A
record: name `match`, value `203.0.113.7`. Check it from your computer once it has spread (minutes,
sometimes an hour):

```sh
dig +short match.example.org        # 203.0.113.7
```

## 3. The server

Build it on your computer (from this repository; it is one program, with nothing else to
install) and copy it over. On Linux on x86-64 the build is already a Linux program; on a Mac or
Windows, add `--target linux`:

```sh
sloppy build tools/rendezvous.jo -o rendezvous
scp rendezvous root@203.0.113.7:/usr/local/bin/rendezvous
```

(Or on the droplet: `curl -fsSL https://sloppy-lang.org/install | bash`, then fetch
`tools/rendezvous.jo` from the repository and build it there the same way.)

On the droplet, a user for it, a secret for TURN (made once, used by coturn and the server), and
the service:

```sh
useradd --system --home-dir /var/lib/rendezvous --create-home --shell /usr/sbin/nologin rendezvous
echo "TURN_SECRET=$(openssl rand -hex 32)" > /etc/rendezvous.env
chmod 600 /etc/rendezvous.env
```

`/etc/systemd/system/rendezvous.service`:

```ini
[Unit]
Description=Matchmaking server for Sloppy games (tools/rendezvous.jo)
After=network-online.target
Wants=network-online.target

[Service]
User=rendezvous
Environment=PORT=7700
Environment=ROOMS=/var/lib/rendezvous/rooms.txt
Environment=TURN=turn:match.example.org:3478
EnvironmentFile=/etc/rendezvous.env
ExecStart=/usr/local/bin/rendezvous
Restart=always
RestartSec=2
LimitNOFILE=8192
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=/var/lib/rendezvous

[Install]
WantedBy=multi-user.target
```

```sh
systemctl daemon-reload
systemctl enable --now rendezvous
journalctl -u rendezvous -n 5       # "rendezvous on port 7700: 0 rooms kept, TURN at turn:match.example.org:3478"
```

From your computer (the same program checks a server):

```sh
./rendezvous check ws://match.example.org:7700
# it gives games a TURN server: turn:match.example.org:3478, user ..., password ...
# ok: a matchmaking server answers at ws://match.example.org:7700
```

## 4. Caddy: wss:// for web pages

```sh
apt install -y caddy
```

`/etc/caddy/Caddyfile` (all of it):

```
match.example.org {
    @ws header Upgrade websocket
    handle @ws {
        reverse_proxy 127.0.0.1:7700
    }
    handle {
        respond 404
    }
}
```

(Only WebSockets go on to the server; anything else gets 404. Scanners find a new name within
minutes, from the public log of certificates, and try their usual pages on it. Each `handle` is
needed: on its own, `respond` goes before `reverse_proxy`, whatever their order in the file.)

```sh
systemctl reload caddy
journalctl -u caddy -n 20 | grep -i certificate     # "certificate obtained successfully"
```

Caddy gets the certificate from Let's Encrypt by itself (the DNS record and port 80 must be in
place first) and renews it. Check from your computer that a WebSocket opens through it:

```sh
curl --http1.1 -s -i --max-time 3 -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: SGVsbG8sIHdvcmxkIQ==" \
  https://match.example.org/ | head -1
# HTTP/1.1 101 Switching Protocols
```

## 5. coturn: the TURN relay

```sh
apt install -y coturn
grep TURN_SECRET /etc/rendezvous.env        # the secret, for the file below
```

`/etc/turnserver.conf` (all of it; the secret is the one above, without `TURN_SECRET=`):

```
listening-port=3478
realm=match.example.org
use-auth-secret
static-auth-secret=THE_SECRET
min-port=49160
max-port=49460
fingerprint
no-tls
no-cli
no-multicast-peers
denied-peer-ip=10.0.0.0-10.255.255.255
denied-peer-ip=172.16.0.0-172.31.255.255
denied-peer-ip=192.168.0.0-192.168.255.255
denied-peer-ip=169.254.0.0-169.254.255.255
total-quota=200
syslog
```

(The denied addresses keep the relay from reaching the droplet's private network and
DigitalOcean's metadata service. A droplet has its public address on its own network card, so
coturn needs no `external-ip`.)

```sh
systemctl enable coturn
systemctl restart coturn
systemctl status coturn --no-pager | head -3     # active (running)
```

(If it will not stay running, `/etc/default/coturn` may need `TURNSERVER_ENABLED=1`.)

To see the relay work: on https://webrtc.github.io/samples/src/content/peerconnection/trickle-ice/,
add `turn:match.example.org:3478` with the user and password `rendezvous check` printed, and
Gather candidates: a line of type `relay` with 203.0.113.7 means it works.

## 6. The games

In a game, `invite.server("wss://match.example.org")` before `invite.from_link()`. Web pages
connect to that; a native build connects to `ws://match.example.org:7700` (the same host, port
7700, worked out from the address). Aces has it as a constant:

```gdscript
const MATCH_SERVER = "wss://match.example.org"
```

Rebuild the game (and the site's pages). To try a server before putting it in a game, any game
that uses `import invite` takes it from the address of its page, `aces.html?server=wss://match.example.org`,
or from `SLOPPY_SERVER=ws://match.example.org:7700` for a native build; add
`&SLOPPY_RTC_RELAY_ONLY=1` to a page's address (on both players' pages) to make it connect through
the TURN relay only.

## Running it

- Logs: `journalctl -u rendezvous` (a line an hour: connections, open rooms, friends waiting).
- A new version: build and copy it as in step 3, then `systemctl restart rendezvous`. The rooms
  are kept in `/var/lib/rendezvous/rooms.txt`, and the games connect again by themselves.
- Limits: messages of 4 KB at most, one room a connection, 30 joins a connection in 10 minutes,
  32 friends waiting in a room, `MAX_CLIENTS` (2000) connections; a connection silent for 150 s
  is closed (games say something every 20 s, but not from a hidden browser tab), and a friend
  waits for a room 30 minutes at most.
  A room not opened for 30 days is forgotten (its code can then be taken by another computer).
- Privacy: the server sees the codes, which hold each game's network addresses (as any server
  that connects players does), and no game traffic. The codes of native programs travel over
  port 7700 without TLS: someone on the path could read or change them. Web pages use wss://.
- Updates to Ubuntu: `apt upgrade` now and then (or `unattended-upgrades`, on by default on
  Ubuntu, for security updates).
