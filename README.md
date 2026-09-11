# herman

**hermes-agent · simple task manager**

herman is a small, dependency-free manager for your
[Hermes Agent](https://hermes-agent.nousresearch.com/docs) projects (profiles): one CLI plus one
local web panel, on top of the `hermes` binary you already have. It never reimplements the agent and
never edits your Hermes config by hand: changes go through `hermes config set`, `hermes profile use`
and `hermes profile delete`.

- every project in one place: create, enter, back up, inspect, rename, delete
- live view: which project has a session open, which gateway runs, what each project costs
- read-only analytics from your own `state.db`: tokens per model and per day, cache ratio, tool
  counters, error digest, history search
- local web panel (loopback only, token plus cookie, POST-only mutations) with its own security
  battery

Nothing is uploaded anywhere. herman reads what Hermes already writes and, when you ask it to, runs
the Hermes CLI.

## Requirements

- Hermes Agent installed and on your PATH (`hermes -V`)
- Python 3.9+ (standard library only, no pip)
- Linux or macOS. Native Windows is not supported yet: herman leans on POSIX signals and `/proc` for
  live sessions and for stopping one politely, so on Windows run it inside WSL2
- a terminal emulator only for the "open a session window" button

## Install

```sh
git clone https://github.com/levay08/herman.git
cd herman && ./install.sh
```

That copies `~/.local/bin/herman`, `~/.local/share/herman/index.html` and the bash completion. You
can also run `./herman -l` and `./herman web` straight from the clone, without installing anything.

## CLI

**Projects**

```sh
herman                       dashboard: every project, its model, skills, memory, live session
herman -p work               create a project (a Hermes profile)
herman work                  enter its Hermes session (hands the terminal over to hermes)
herman -u 2                  enter project number 2
herman -l | -i [name]        list projects / inspect one
herman -r <name>             delete a project and its profile
herman -d [name|--all]       doctor: read-only health check
herman sync [--fix]          re-check herman against the installed Hermes
```

**Sessions, models, history**

```sh
herman kill <name> [session-id]        stop a running session (SIGINT first, like Ctrl+C)
herman model [name]                    current model and provider
herman model <name> --list             models your endpoint offers, with prices
herman model <name> --set <id>         switch model (--provider <p> changes the provider)
herman history <name> --stats          sessions, messages and usage rows
herman history <name> --delete-matching <q> | --delete-session <id> | --delete-all
herman --usage [--days N]              tokens and estimated cost
herman -b <name|--all>                 back up to ~/Documents/herman-backup/
herman -x <file> [--as name]           restore a backup
herman --tidy [--all] | --logs <name>  free disk space / read the agent log
```

**Git and access**

```sh
herman git [name] ...        repo status, init, identity, remotes, credential helper
herman -C <name> [path]      show or set the workdir (terminal.cwd in the Hermes config)
herman access [name]         API keys, SSH keys, known hosts, git credentials, live connections
herman access grant user@host   key + ssh-config entry + ssh-copy-id in one step
herman access set-env <p> <VAR> add or update an API key in the project .env (0600)
```

**Web and maintenance**

```sh
herman web [--port 9120]     start the panel and open it
herman web --url             print the full URL including the access token
herman web --status | --stop which panels run / stop one
herman security [--json]     security regression battery for the running panel
herman -h                    every command, including the ones not shown here
```

## Web panel

```sh
herman web
```

Serves `127.0.0.1:9120` and prints a URL carrying a random token. The token is exchanged for an
`HttpOnly` cookie on first load, so it does not stay in your address bar, history or link referrers.

- **Dashboard** all-project overview plus total token usage
- **Projects** one card per project (model, workdir, skills, memory, live session); actions stream
  their output into the console at the bottom
- **Model** current model, model changer and the token usage board
- **Insights** history search (click a hit to read the full message), activity, tool counters,
  context health, error digest
- **Access** API keys, SSH keys and hosts, git identity, credentials, live SSH connections
- **Maintenance** backups, disk space, about

Notes: the panel listens on loopback only, and everything inside it that changes state asks you to
type the project name first. The Hermes dashboard (chat, config, keys, MCP, webhooks) stays at
`hermes dashboard`, port 9119.

## Docker

For any OS with Docker (Linux, macOS, Windows with Docker Desktop). The image contains Hermes and
herman; your Hermes data comes from the host mount, so the panel shows your own projects.

```sh
docker compose up --build                      # panel at http://127.0.0.1:9120
docker compose exec herman herman web --url    # the URL including its access token
docker compose exec herman herman -l           # the CLI inside the container
```

Without Compose:

```sh
docker build -t herman .
docker run --rm -v "$HOME/.hermes:/home/herman/.hermes" -p 127.0.0.1:9120:9120 herman
docker run --rm -it -v "$HOME/.hermes:/home/herman/.hermes" herman -l
```

- the port mapping keeps the panel on your machine; keep it that way unless you front it with a
  reverse proxy
- mount `~/.hermes` read-only (add `:ro`) for a view-only panel: listing, usage, insights and search
  keep working, actions that write will refuse
- `Enter session` and the terminal window need a desktop, so run those from the host CLI
- the engine version inside the image can drift from your host install:
  `docker build --build-arg HERMES_BRANCH=<branch> -t herman .` pins it
- the code is baked into the image, so after pulling changes run `docker compose up --build` again
- inside the container the per-project shortcut commands are not needed and not reported as missing;
  the engine binary, profiles and data still come from your own installation and mount

## Troubleshooting

- `herman: command not found`: add `~/.local/bin` to your `PATH`.
- The panel looks stale after an upgrade: `herman web --stop && herman web` (Python is kept in memory).
- Port already in use: `herman web --port 9121`.
- `gateway: down` on a project: no messaging gateway (Telegram, Discord, ...) runs for it. Harmless.
- A session is stuck: `herman kill <project>`, or `herman kill <project> <session-id>`.

## Uninstall

```sh
herman web --stop
rm -f  ~/.local/bin/herman
rm -rf ~/.local/share/herman
```

Your Hermes profiles, sessions and configuration are untouched: herman never owned them.

## License

MIT, see [LICENSE](LICENSE). herman is an unofficial companion tool for Hermes Agent and is not
affiliated with Nous Research.
