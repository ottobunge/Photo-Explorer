{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  name = "photo-explorer";

  buildInputs = with pkgs; [
    # Task runner
    go-task

    # Docker
    docker
    docker-compose

    # Python (for backend)
    python312
    python312Packages.pip
    python312Packages.virtualenv
    poetry

    # Node.js (for frontend)
    nodejs_20
    nodePackages.pnpm

    # Database tools
    postgresql_15

    # Development utilities
    git
    jq
    curl
    httpie

    # Process manager for local development
    overmind
    tmux  # Required by overmind

    # Google Cloud CLI
    google-cloud-sdk

    # For ML models (optional, can use Docker instead)
    # cudaPackages.cudatoolkit
  ];

  shellHook = ''
    echo "Photo Explorer Development Environment"
    echo "======================================="
    echo ""
    echo "Available commands:"
    echo "  task          - Run tasks (see Taskfile.yml)"
    echo "  task --list   - List all available tasks"
    echo ""
    echo "Quick start:"
    echo "  task setup        - Initial project setup"
    echo "  task dev:local    - Local dev (infra in Docker, app local) ⭐ RECOMMENDED"
    echo "  task dev          - Start all services in development mode"
    echo "  task test         - Run all tests"
    echo "  task models:setup - Download AI models (CLIP, face detection)"
    echo ""
    echo "See DEV_WORKFLOW.md for detailed development guide"
    echo ""

    # Set up Python virtual environment path
    export VIRTUAL_ENV="$PWD/backend/.venv"
    export PATH="$VIRTUAL_ENV/bin:$PATH"

    # Set up Node modules path
    export PATH="$PWD/frontend/node_modules/.bin:$PATH"

    # Load environment variables from .env if it exists
    if [ -f .env ]; then
      set -a
      source .env
      set +a
      echo "Loaded environment variables from .env"
    fi
  '';
}
