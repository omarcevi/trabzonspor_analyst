# Installs uv, the Python package manager, if this machine does not have it yet.
# Run it with source, so that this terminal finds uv right after the install:
#     source scripts/install_uv.sh
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  . "$HOME/.local/bin/env"
fi
uv --version
