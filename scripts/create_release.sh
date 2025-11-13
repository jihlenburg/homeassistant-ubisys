#!/bin/bash
# Script to create a GitHub release with CHANGELOG content
# Usage: ./scripts/create_release.sh v1.2.1

set -e

VERSION="$1"
if [ -z "$VERSION" ]; then
    echo "Usage: $0 <version-tag>"
    echo "Example: $0 v1.2.1"
    exit 1
fi

# Check if tag exists
if ! git rev-parse "$VERSION" >/dev/null 2>&1; then
    echo "Error: Tag $VERSION does not exist"
    echo "Create it first with: git tag -a $VERSION -m 'Release $VERSION'"
    exit 1
fi

# Extract release notes from CHANGELOG.md
# This assumes your CHANGELOG follows Keep a Changelog format
echo "Extracting release notes for $VERSION from CHANGELOG.md..."

# Get the version without 'v' prefix for CHANGELOG lookup
VERSION_NUMBER="${VERSION#v}"

# Extract the section between [VERSION] and the next version heading
# Using sed for portable extraction
RELEASE_NOTES=$(sed -n "/^## \[${VERSION_NUMBER}\]/,/^## \[/{
    /^## \[${VERSION_NUMBER}\]/d
    /^## \[/q
    p
}" CHANGELOG.md)

if [ -z "$RELEASE_NOTES" ]; then
    echo "Warning: No release notes found in CHANGELOG.md for version $VERSION_NUMBER"
    echo "Creating release with generic message..."
    RELEASE_NOTES="Release $VERSION

See [CHANGELOG.md](https://github.com/jihlenburg/homeassistant-ubisys/blob/main/CHANGELOG.md) for details."
fi

# Create GitHub release using gh CLI
echo "Creating GitHub release for $VERSION..."
echo "$RELEASE_NOTES" | gh release create "$VERSION" \
    --title "$VERSION" \
    --notes-file - \
    --verify-tag

echo "✓ Release $VERSION created successfully!"
echo "View at: https://github.com/jihlenburg/homeassistant-ubisys/releases/tag/$VERSION"
