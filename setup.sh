#!/usr/bin/env bash

if [ ! -d "$PWD/.venv" ]; then
  echo "Create a virtual environment"
  python3 -m venv .venv --prompt unit0-examples
  source .venv/bin/activate

  if [[ "$(uname)" == "Darwin" ]]; then
    # Otherwise python-axolotl-curve25519 won't compile
    export CC=gcc
  fi

  echo "Install dependencies"
  pip install .
fi

echo "Done."
