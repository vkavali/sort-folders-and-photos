#!/usr/bin/env bash
# Build Semantic File Aggregator as a standalone desktop app (macOS / Linux).
# Usage: ./build.sh

set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found in PATH. Install Python 3.10+ and try again." >&2
    exit 1
fi

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m pip install pyinstaller

rm -rf build dist

python3 -m PyInstaller --noconfirm SemanticFileAggregator.spec

echo
echo "============================================================"
echo "Build complete."
echo "  Folder bundle: dist/SemanticFileAggregator/"
case "$(uname -s)" in
    Darwin)
        echo "  App bundle:    dist/SemanticFileAggregator.app  (drag to /Applications)"
        ;;
    *)
        echo "  Launcher:      dist/SemanticFileAggregator/SemanticFileAggregator"
        ;;
esac
echo "============================================================"
