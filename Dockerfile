# herman in a container: the CLI and the web panel, together with the Hermes engine they drive.
#
# Quick use (see README for details):
#   docker build -t herman .
#   docker run --rm -it -v "$HOME/.hermes:/home/herman/.hermes" herman -l
#   docker run --rm -v "$HOME/.hermes:/home/herman/.hermes" -p 127.0.0.1:9120:9120 herman
#   docker compose up --build
#
# Your Hermes data directory is mounted from the host, so the panel shows YOUR projects. The engine
# itself lives at /opt/hermes-agent inside the image, outside that mount, so it is never shadowed by
# a host install (a Windows or macOS Hermes venv would not run in here anyway).
FROM python:3.11-slim-bookworm

# Pin the engine to the branch you actually run on the host if you want zero drift:
#   docker build --build-arg HERMES_BRANCH=main -t herman .
ARG HERMES_BRANCH=main
ARG HERMES_INSTALL_DIR=/opt/hermes-agent

ENV DEBIAN_FRONTEND=noninteractive \
    HERMES_INSTALL_DIR=${HERMES_INSTALL_DIR} \
    HERMES_HOME=/home/herman/.hermes \
    PATH=/home/herman/.local/bin:/usr/local/bin:/usr/bin:/bin \
    PYTHONUNBUFFERED=1

# bash + curl for the installer, git for its clone, libatomic1 because the engine's runtime wants it
# on Debian/Ubuntu, openssh-client for `herman access`, tini to reap the process tree.
RUN apt-get update \
 && apt-get install -y --no-install-recommends bash ca-certificates curl git libatomic1 openssh-client tini \
 && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash herman

USER herman
WORKDIR /home/herman

# 1. Hermes Agent: no wizard, no browser bundle (a container has no desktop, and herman never needs it)
RUN curl -fsSL https://hermes-agent.nousresearch.com/install.sh \
    | bash -s -- --non-interactive --skip-setup --no-playwright --branch "$HERMES_BRANCH" \
                 --hermes-home "$HERMES_HOME" \
 && hermes --version

# 2. herman: the CLI, the panel page and the two helper scripts, installed with the same script the
#    README tells people to run, so the image and a local install cannot drift apart.
COPY --chown=herman:herman herman index.html caduceus.png security_check.py preflight.py install.sh /tmp/herman-src/
COPY --chown=herman:herman completions/herman /tmp/herman-src/completions/herman
RUN sh /tmp/herman-src/install.sh \
 && rm -rf /tmp/herman-src \
 && herman -h > /dev/null

# 3. entrypoint: start the panel (and print its URL) when given no arguments, otherwise run the CLI
COPY --chown=herman:herman docker-entrypoint.sh /home/herman/.local/bin/herman-entrypoint
RUN chmod 0755 /home/herman/.local/bin/herman-entrypoint

EXPOSE 9120
VOLUME ["/home/herman/.hermes"]

# The panel is bound to 0.0.0.0 inside the container on purpose (that is how a published port reaches
# it) and --allow-external acknowledges it; publish it to 127.0.0.1 on the host (see compose file) so
# it stays a local panel.
ENTRYPOINT ["/usr/bin/tini", "--", "/home/herman/.local/bin/herman-entrypoint"]
CMD []
