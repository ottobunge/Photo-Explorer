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

    # Required for NumPy/ML libraries in NixOS
    stdenv.cc.cc.lib
    zlib

    # For ML models (optional, can use Docker instead)
    # cudaPackages.cudatoolkit

    # Playwright browsers
    playwright-driver.browsers

    # Playwright system dependencies
    glib
    nss
    nspr
    dbus
    atk
    at-spi2-atk
    expat
    xorg.libX11
    xorg.libXcomposite
    xorg.libXdamage
    xorg.libXext
    xorg.libXfixes
    xorg.libXrandr
    mesa # provides libgbm
    xorg.libxcb
    libxkbcommon
    systemd # provides libudev
    alsa-lib
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

    # Fix for NumPy/ML libraries in NixOS - add standard library paths
    export LD_LIBRARY_PATH="${pkgs.stdenv.cc.cc.lib}/lib:${pkgs.zlib}/lib''${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

    # Set Playwright browsers path (use Nix-provided browsers, don't run playwright install)
    export PLAYWRIGHT_BROWSERS_PATH="${pkgs.playwright-driver.browsers}"

    # Skip Playwright's host requirements validation (NixOS handles dependencies differently)
    export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true

    # Set library path for Playwright browser dependencies
    export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath [
      pkgs.glib
      pkgs.nss
      pkgs.nspr
      pkgs.dbus
      pkgs.atk
      pkgs.at-spi2-atk
      pkgs.expat
      pkgs.xorg.libX11
      pkgs.xorg.libXcomposite
      pkgs.xorg.libXdamage
      pkgs.xorg.libXext
      pkgs.xorg.libXfixes
      pkgs.xorg.libXrandr
      pkgs.mesa
      pkgs.xorg.libxcb
      pkgs.libxkbcommon
      pkgs.systemd
      pkgs.alsa-lib
    ]}:$LD_LIBRARY_PATH"

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
