#!/bin/sh
# Adds a content hash to the names of static files (images, fonts, CSS, JS) and updates every reference.
# A changed file gets a new name, so files can be cached for a year without ever serving a stale version.
# Every .html page of the site (home, subfolders, 404) is updated, as well as styles.css and script.js.
# Usage: fingerprint.sh <site folder>
set -eu
cd "$1"

esc() { printf '%s' "$1" | sed 's/[.]/\\./g'; }
HTML=$(find . -name '*.html')
rename() { # existing relative path -> hashed path, references updated
  old=$1
  h=$(md5sum "$old" | cut -c1-10)
  new="${old%.*}.$h.${old##*.}"
  mv "$old" "$new"
  # shellcheck disable=SC2086
  sed -i "s|$(esc "$old")|$new|g" $HTML $(ls styles*.css script*.js)
}

# Images and fonts first: the CSS and JS hashes must account for the rewritten names.
for f in images/*.webp images/*.png images/*.svg fonts/*.woff2; do
  [ -f "$f" ] || continue   # a glob with no match stays as a literal string
  rename "$f"
done
rename styles.css
rename script.js

# Safeguard: every local reference must point to a file that exists.
missing=0
for ref in $(cat $HTML styles.*.css script.*.js | grep -oE '(images|fonts)/[A-Za-z0-9._-]+\.[a-z0-9]+|styles\.[0-9a-f]{10}\.css|script\.[0-9a-f]{10}\.js' | sort -u); do
  [ -f "$ref" ] || { echo "Broken reference: $ref" >&2; missing=1; }
done
[ "$missing" = 0 ]
