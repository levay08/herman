#!/bin/sh
# Container entrypoint.
#
#   (no arguments)        start the panel on 0.0.0.0:$HERMAN_PORT and print its URL
#   docker run herman -l  any herman CLI command runs as it is
#
# Binding a wildcard inside the container is what lets a published port reach the panel; the URL it
# prints is loopback, so copy that into your own browser (the port mapping in docker-compose.yml
# publishes it on 127.0.0.1).
set -eu

PORT="${HERMAN_PORT:-9120}"
BIND="${HERMAN_BIND:-0.0.0.0}"

if [ "$#" -eq 0 ]; then
    set -- web --host "$BIND" --allow-external --port "$PORT" --no-open
fi

if [ "$1" != "web" ]; then
    exec herman "$@"                       # a plain CLI call, no background panel
fi

herman "$@" &
panel=$!
trap 'kill -TERM "$panel" 2>/dev/null || true' TERM INT

# wait for the panel to answer, then print the full URL once (it carries the access token)
i=0
while [ "$i" -lt 120 ]; do
    if herman web --status --port "$PORT" 2>/dev/null | grep -q "running"; then
        break
    fi
    i=$((i + 1))
    sleep 0.25
done

printf '\n'
if herman web --url --port "$PORT" 2>/dev/null; then
    printf 'open that URL in your browser (it carries the access token)\n'
    printf 'CLI in this container: docker compose exec herman herman -l\n'
else
    printf 'the panel did not answer on port %s; see the log above\n' "$PORT"
fi

wait "$panel"
