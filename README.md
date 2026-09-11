# herman

**hermes-agent · simple task manager**

`herman` is a small, dependency-free manager for your [Hermes Agent](https://hermes-agent.nousresearch.com/docs)
projects (profiles). It is one CLI plus one local web panel, and it sits on top of the `hermes`
binary you already have: herman never reimplements the agent and never rewrites your Hermes
configuration behind your back. Every change goes through `hermes config set`,
`hermes profile use` or `hermes profile delete`.

What you get:

- one place for every project: create, enter, back up, inspect, rename, delete
- a live view: which project has a session open right now, which gateway is running, how much each
  project costs
- read-only analytics from your own `state.db`: token usage per model and per day, cache ratio,
  tool counters, context health, an error digest and full history search
- a local web panel (loopback only, token + cookie, mutations only over POST) that ships with its
  own security regression battery

Nothing is uploaded anywhere. herman reads the files Hermes already writes and, when you ask it to,
runs the Hermes CLI.

## Requirements

- **Hermes Agent** installed and reachable as `hermes` (check with `hermes -V`)
- **Python 3.9+** (standard library only, no pip, no virtualenv)
- Linux or macOS. A terminal emulator (terminator, gnome-terminal, konsole, kitty, alacritty,
  xterm) is only needed for the "open a session in a new window" button

## Install

```sh
git clone https://github.com/levay08/herman.git
cd herman
./install.sh
```

The installer copies three things into `~/.local` and prints what it did:

```
~/.local/bin/herman                                     the CLI + web server
~/.local/share/herman/index.html                        the panel page
~/.local/share/bash-completion/completions/herman        bash completion
```

Prefer to do it by hand:

```sh
install -Dm755 herman          ~/.local/bin/herman
install -Dm644 index.html      ~/.local/share/herman/index.html
install -Dm644 completions/herman ~/.local/share/bash-completion/completions/herman
```

You can also run straight from the clone without installing anything: `./herman -l` and
`./herman web` work from the repository directory.

## Quick start

```sh
herman                  # dashboard: every project, its model, skills, memory, live sessions
herman -p work          # create a project called "work" (a Hermes profile)
herman work             # enter its Hermes session (hands the terminal over to hermes)
herman -u 2             # enter project number 2 from the list
herman web              # open the local control panel
herman -h               # the full command list
```

## CLI reference

**Projects**

```sh
herman -l                       list projects with numbers, model, skills, memory, live session
herman -i [name]                one project in detail (paths, model, gateway, sessions)
herman -p <name>                create a project (--clone, --clone-all, --from <src>, --no-skills)
herman --rename <old> <new>     rename a project
herman --alias <name>           shortcut command for a project (--alias-remove drops it)
herman -r <name>                delete a project and its profile
herman -d [name|--all]          doctor: read-only health check
herman --audit [name]           memory + skills summary
herman --unused [days]          projects idle for N days
herman sync [--fix]             re-check herman against the installed Hermes
```

**Sessions**

```sh
herman <name> | herman <number> | herman -u [name]   enter a session
herman -u <name> -q "prompt"    one-shot question (cron/scripts); -q - reads stdin
herman kill <name> [session-id] stop a running session (SIGINT first, like Ctrl+C)
herman --status                 every live session with pid, surface and uptime
```

**Model, history and space**

```sh
herman model [name]             current model and provider
herman model <name> --list      models your endpoint offers (+ prices, refresh with --refresh)
herman model <name> --set <id>  switch model (--provider <p> changes the provider)
herman history <name> --stats   sessions, messages and usage rows
herman history <name> --delete-matching <q> | --delete-session <id> | --delete-message <id> | --delete-all
herman --usage [--days N]       token usage and estimated cost
herman -b <name|--all>          back up to ~/Documents/herman-backup/<name>-<stamp>.tar.gz
herman -x <file> [--as name]    restore a backup
herman --tidy [name|--all]      free disk space
herman --logs <name> [-f]       read or follow the agent log
```

**Git and access**

```sh
herman git [name]               repo status of the project workdir
herman git <name> init          create a repository
herman git <name> set-user --name N --email E      repo-local git identity
herman git <name> set-remote <n> <url> | rm-remote <n> | set-helper store|none
herman -C <name> [path]         show or set the workdir (terminal.cwd in the Hermes config)
herman access [name]            API keys, SSH keys, known hosts, git credentials, live connections
herman access grant user@host   set up SSH access (key + ssh-config entry + ssh-copy-id)
herman access set-env <p> <VAR> add or update an API key in the project .env (0600)
```

**Web panel and maintenance**

```sh
herman web [--port 9120]        start the panel and open it
herman web --url                print the full URL including the access token
herman web --status | --stop    which panels are running / stop one
herman security [--json]        run the panel's security regression battery (38 checks)
herman completion install       install shell completion
```

## Web panel

```sh
herman web
```

`herman web` starts a small local server (default `127.0.0.1:9120`) and prints a URL that carries a
random access token. The token is exchanged for an `HttpOnly` cookie on first load, so it does not
stay in your address bar, browser history or in the `Referer` of links the page opens.

Boards:

- **Dashboard** overview of every project plus all-project token usage
- **Projects** one card per project (model, workdir, skills, memory, live session) with the actions
  that stream their output into the console at the bottom
- **Model** current model, model changer and the token usage board
- **Insights** history search (click a hit to read the full message), activity, tool counters,
  context health, error digest, history deletion
- **Access** API keys, SSH keys and hosts, git identity, credentials, live SSH connections
- **Maintenance** backups, disk space, this project, about

Keep in mind:

- the panel binds to loopback. `--host 0.0.0.0` is refused unless you pass `--allow-external`,
  because the panel is token-only over plain HTTP
- anything that changes state is a POST, and destructive actions ask you to type the project name
- usage and insights are read-only reads of your `state.db` (`?mode=ro`), so the panel never becomes
  a second writer next to a running Hermes
- the Hermes dashboard (chat, config, keys, MCP, webhooks) stays at `hermes dashboard`, port 9119.
  herman only links to it

## It adapts to your Hermes, not the other way around

herman has no provider of its own. It reads, per project:

| what | where |
|---|---|
| model, provider, base_url, API key | that project's `config.yaml` (`model.*`) |
| workdir | `terminal.cwd` in the same file |
| live sessions | `<project>/runtime/active_sessions.json` (pid + start time, so a recycled pid is ignored) |
| gateway status | `<project>/gateway_state.json`, decided by pid liveness like Hermes does |
| usage, insights, history | `state.db`, always opened read-only |
| prices (estimate) | Hermes' own `models_dev_cache.json` |
| model list | first `{base_url}/v1/models` when the project has a custom endpoint (the API key is sent only if the project has one), otherwise Hermes' local caches |

So the model picker follows **your** provider:

- custom `base_url` (a gateway, a local server, a proxy): herman asks that endpoint
- a plain provider such as `openai`, `anthropic` or `nous` with no `base_url`: herman shows what
  Hermes itself knows, prices included
- an endpoint that is down: herman falls back to Hermes' cache, then to your own optional
  `models-local.json`, then to the configured model, and never errors out

There is nothing to configure inside herman for this. If you change provider or model with
`herman model`, the change is written with `hermes config set`, so the CLI, the desktop app and the
gateway all see it.

## Security

- random 192-bit token, compared in constant time, exchanged for an `HttpOnly; SameSite=Strict` cookie
- cross-site requests, foreign `Origin` headers and foreign `Host` headers (DNS rebinding) are refused
- state changes are POST-only, so a prefetch or an image tag cannot delete anything
- values that reach a child process are shape-checked, so nothing can smuggle a command line flag
- every response carries `nosniff`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY` and a
  restrictive CSP
- token, pid, state and backups are `0600` in a `0700` cache directory; passwords never reach a
  command line (SSH uses an askpass helper, the secret travels through the environment)
- destructive operations back up first: history deletion copies `state.db` (WAL-safe) before touching
  anything and never touches a session that is running

Verify it yourself at any time, against your own running panel:

```sh
herman security
# 38 checks · 38 ok · 0 failed
```

`security_check.py` and `preflight.py` in this repository are the enforcement: the first runs the
probes above over HTTP, the second scans the publishable files for operator data before a release.

## Optional extras

- `~/.local/share/herman/models-local.json` is **your** data: an optional catalog
  (`{"models": [{"id": ..., "provider": ..., "context": ..., "input_usd": ...}]}`) used to enrich or
  replace a model list. It is never shipped and never overwritten.
- `caduceus.png` is the decorative watermark on the dashboard. It is optional: without it the
  dashboard simply has no pattern.

## Troubleshooting

- **`herman: command not found`**: `~/.local/bin` is not on your `PATH` (see the installer note).
- **`error: Hermes is not installed`**: herman needs the `hermes` binary; install Hermes first.
- **Panel says "no project" or the page looks stale**: HTML is re-read on every request but the
  running panel keeps its Python in memory. After upgrading herman, restart it:
  `herman web --stop && herman web`.
- **Port already in use**: `herman web --port 9121`.
- **`gateway: down`**: the messaging gateway (Telegram, Discord, ...) for that project is not
  running. That is normal if you never set one up and it affects nothing else.
- **A session is stuck**: `herman kill <project>`, or `herman kill <project> <session-id>` for one
  of several. It interrupts first, exactly like Ctrl+C, and only kills as a last resort.

## Uninstall

```sh
herman web --stop
rm -f  ~/.local/bin/herman
rm -rf ~/.local/share/herman
rm -f  ~/.local/share/bash-completion/completions/herman
```

Your Hermes profiles, sessions and configuration are untouched: herman never owned them.

## Repository layout

```
herman                 the whole CLI and web server (single stdlib-only Python file)
index.html             the web panel (single file: HTML, CSS, JS)
caduceus.png           optional dashboard watermark
security_check.py      security regression battery (`herman security`)
preflight.py           scans the publishable files for operator data
completions/herman     bash completion
install.sh             copies the pieces into ~/.local
```

## License

MIT, see [LICENSE](LICENSE).

herman is an unofficial companion tool for Hermes Agent and is not affiliated with Nous Research.
