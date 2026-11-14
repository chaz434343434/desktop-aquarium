#!/bin/sh
# Builds the web version and puts it online at https://desktop-aquarium.pages.dev/play/
# (needs `npx wrangler login` once). Run from the project folder: sh build_assets/publish_web.sh
set -e
python build_assets/build_web.py
rm -rf server/pages/public/play
mkdir -p server/pages/public/play
cp build_web/src/build/web/index.html build_web/src/build/web/src.apk build_web/src/build/web/src.tar.gz \
   build_web/src/build/web/favicon.png server/pages/public/play/
cd server/pages
npx --yes wrangler@4.36.0 pages deploy public --project-name desktop-aquarium --branch main --commit-dirty=true
