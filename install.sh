#!/bin/sh
# herman installer: copies the tool into ~/.local (no root, no pip, stdlib only).
#
#   ./install.sh              install for the current user
#   PREFIX=/somewhere ./install.sh
#
# It never touches ~/.hermes, your Hermes config or any existing project: herman is a read-mostly
# companion that talks to the `hermes` binary you already have.
set -eu

SRC=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PREFIX="${PREFIX:-$HOME/.local}"
BIN="$PREFIX/bin"
SHARE="$PREFIX/share/herman"
COMP="$PREFIX/share/bash-completion/completions"

install -d -m 0755 "$BIN" "$SHARE" "$COMP"
install -m 0755 "$SRC/herman" "$BIN/herman"
install -m 0644 "$SRC/index.html" "$SHARE/index.html"
install -m 0644 "$SRC/icons.svg" "$SHARE/icons.svg"
install -m 0644 "$SRC/icons.LICENSE.txt" "$SHARE/icons.LICENSE.txt"
install -m 0644 "$SRC/security_check.py" "$SHARE/security_check.py"
install -m 0644 "$SRC/preflight.py" "$SHARE/preflight.py"
install -m 0755 "$SRC/panel-syntax-check.sh" "$SHARE/panel-syntax-check.sh"
install -m 0644 "$SRC/completions/herman" "$COMP/herman"
if [ -f "$SRC/caduceus.png" ]; then
    install -m 0644 "$SRC/caduceus.png" "$SHARE/caduceus.png"
fi

# models-local.json is USER DATA and is deliberately never shipped or overwritten.
if [ ! -f "$SHARE/models-local.json" ]; then
    : # herman works without it: the model list comes from your endpoint or from Hermes itself
fi

printf 'installed:\n  %s\n  %s\n  %s\n' "$BIN/herman" "$SHARE/index.html" "$COMP/herman"

if ! command -v hermes >/dev/null 2>&1; then
    printf '\nwarning: `hermes` is not on your PATH. herman needs it:\n'
    printf '  curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash\n'
fi

case ":$PATH:" in
    *":$BIN:"*) ;;
    *) printf '\nnote: %s is not on your PATH yet. Add it, for example:\n  export PATH="%s:$PATH"\n' "$BIN" "$BIN" ;;
esac

printf '\ntry it:\n  herman            # project dashboard\n  herman -p work    # create a project called "work"\n  herman work        # enter its Hermes session\n  herman web         # local control panel in the browser\n'
