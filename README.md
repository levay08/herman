# herman

**hermes-agent · simple task manager**

A small, dependency-free manager for your
[Hermes Agent](https://hermes-agent.nousresearch.com/docs) projects (profiles): one CLI and one local
web panel on top of the `hermes` binary you already have. Create, enter, back up, inspect and delete
projects; see what runs and what each one costs; read the analytics Hermes already writes to
`state.db`. It never reimplements the agent — sessions, model switches and profile changes go through
`hermes`, and the settings herman writes itself land in one project's own `config.yaml` / `.env`,
after a backup. It uploads nothing anywhere.

## Install

```sh
git clone https://github.com/levay08/herman.git
cd herman && ./install.sh
```

Hermes on your PATH (`hermes -V`) and Python 3.9+ (standard library only). Linux or macOS; on Windows
run it inside WSL2. It copies `~/.local/bin/herman`, `~/.local/share/herman/index.html` and the bash
completion — or run `./herman -l` and `./herman web` straight from the clone.

## Use

```sh
herman                  dashboard: every project, its model, skills, memory, live session
herman <name>           enter that project's Hermes session
herman web              local panel at 127.0.0.1:9120
herman -h               every command, grouped
```

The project is implicit (the one you are working in, else the last one you used), values are
positional, a setting is `key=value`:

```sh
herman model opus | model @URL       switch the model / the endpoint
herman c tg on | c web backend=exa   chat platform, web backend
herman m add docs URL                MCP server
herman key EXA_API_KEY               store a key in the project's .env
herman kill [name]                   stop a running session (Ctrl+C style, SIGINT first)
herman last [--all]                  CLOSED sessions of the rolling last 24 h, and what they left
herman usage | hist | logs | backup  tokens and cost, history, log, backup
herman -d | sec                      health check (fixable with `herman -d fix`) / security battery
```

`herman -h` is the full list. The short spellings are what it leads with, and the long ones keep
working (`herman config <name> chat telegram --enable`, `mcp add <server> --url …`).

### Why it is shorter than the engine it wraps

| job | hermes | herman |
|---|---|---|
| enter a session | `hermes -p web` | `herman web` |
| switch model | `hermes -p web config set model.default opus` | `herman model opus` |
| switch endpoint | `hermes -p web config set model.base_url URL` | `herman model @URL` |
| enable telegram | `hermes -p web gateway setup` | `herman c tg on` |
| a chat setting | `hermes -p web config set telegram.require_mention false` | `herman c tg require_mention=false` |
| web backend | `hermes -p web config set web.backend exa` | `herman c web backend=exa` |
| a backend key | (edit `.env` by hand) | `herman c web EXA_API_KEY` |
| add an MCP server | `hermes -p web mcp add docs --url URL` | `herman m add docs URL` |
| project history | `hermes -p web insights` | `herman hist` |
| health check | `hermes -p web doctor` | `herman -d` |

Across the 18 jobs where both CLIs have a verb: hermes 101 words, herman 59.

## Update

```sh
herman update --check | --dry-run | --no-restart
```

herman's own files only (CLI, panel, assets, completion in the install prefix); `~/.hermes` is never
written, so no project, profile, session or memory file is in the payload, and running Hermes
sessions are unaffected. Replaced files are backed up under `~/.cache/herman/update/`. The same from
the panel: **Maintenance → About**.

## Web panel

![herman web panel](herman_web.png)

`herman web` prints a URL carrying a random token, exchanged on first load for an `HttpOnly`,
`SameSite=Strict` cookie that survives restarts, so the token never stays in your address bar.

- **Dashboard** all-project overview plus total token usage
- **Projects** one card per project (model, workdir, skills, memory, live session), note and name
  editable on the card, drag to reorder, pin up to three
- **Model** model and endpoint, the project's skills, and memory against its budget
- **Insights** history search across every project, activity, tools, context health, errors, and
  **Last session** (closed sessions of the last 24 h: last prompt, last result)
- **Access** keys, SSH, git identity and live connections, plus **Integrations** (chat platforms, web
  backends), **MCP** servers, **Maintenance** (backups, disk, version card)

Loopback only. Every write is a POST and asks you to type the name it is about to touch; the panel
builds the same `herman config` command the CLI accepts. Only the skill search reaches the network.
The Hermes dashboard itself stays at `hermes dashboard` (port 9119).

## Docker

For any OS with Docker: the image contains Hermes and herman, your data comes from the host mount.

```sh
docker compose up --build                      # panel at http://127.0.0.1:9120
docker compose exec herman herman web --url    # the URL including its access token
```

- mount `~/.hermes` read-only (`:ro`) for a view-only panel: reads keep working, writes refuse
- `Enter session` and the terminal window need a desktop: run those from the host CLI
- re-run `docker compose up --build` after pulling changes; `--build-arg HERMES_BRANCH=<branch>` pins
  the engine inside the image

## Troubleshooting

- `herman: command not found`: add `~/.local/bin` to your `PATH`.
- The panel looks stale after an upgrade: `herman web --stop && herman web`.
- A tab says its panel session ended: the token was rotated or site data was cleared. Reopen the panel
  from the taskbar icon, or from `herman web --url`.
- Port already in use: `herman web --port 9121`.
- A session is stuck: `herman kill <project> [session-id]`.
- `127.0.0.1:9119` shows nothing: nothing is listening. herman's **Open dashboard** button starts it.

## Keeping your data out of the history

Profiles and sessions live in `~/.hermes`; the panel token, the pid file and your project
descriptions live in `~/.cache/herman/`. Nothing user-owned is written into the working tree.
`preflight.py` is the release gate — it scans what you are about to publish for personal paths,
hosts, secrets, session ids, your own project descriptions and the panel token
(`python3 preflight.py --install-hook .` makes it a pre-commit hook). `panel-syntax-check.sh` parses
the panel's JavaScript, which `herman security` runs as one of its checks.

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
