#!/usr/bin/env bash
set -e
function die() {
    echo -e "FATAL: $@"
    exit 2
}


root=$(readlink -f "$(dirname $0)/..")
release_dir="$root/releases"
[ -d "$release_dir" ] || mkdir -p "$release_dir"

echo "Checking for uncommitted changes..."
files=$(git diff --cached --exit-code --name-only) || die "You have staged Git changes. Commit or stash: \n $files"
files=$(git diff --exit-code --name-only) || die "You have unstaged Git changes. Commit or stash: \n $files"

pushd "$root/dist" >/dev/null
version=${1:-latest}
echo "<<<< Doing release build for version '$version'. Continue?... >>>>"
if [ "$1" != "-y" ]; then
    read -n 1 -p "Continue? (ctrl-c to abort)"
fi

$(dirname $0)/compile-translations

echo -e "\nContinuing with build...\n"
output="squeeze-alexa-release-$version.zip"

RELEASE_EXCLUDES=$(tr '\n' ' ' <<< """
*.pem
*.crt
*.key
*.pyc
*__pycache__/*
*.pytest_cache/*
*.cache/*
*.po
*~
*.egg-info/*
*bin/release*
*-translations
test-results""")

echo "Creating ZIP (excluding $RELEASE_EXCLUDES)"
rm "$release_dir/$output" 2>/dev/null || true
zip -r "$release_dir/$output" * -x $RELEASE_EXCLUDES
cd "$root"
echo -e "\nSuccess! Created release ZIP: ($(ls -sh "$output"))"
popd >/dev/null
