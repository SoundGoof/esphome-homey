#!/usr/bin/env bash
# Populate ./fonts from files already on this machine.
#
# The device never fetches anything at runtime — fonts are compiled into the
# firmware — and this keeps the *build* offline too: no gfonts:// and no
# type: web. Font binaries stay out of git, so run this once per checkout.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p fonts

copy_first() {
  local dest="$1"; shift
  for src in "$@"; do
    if [ -f "$src" ]; then
      cp -f "$src" "fonts/$dest"
      echo "  $dest  <-  $src"
      return 0
    fi
  done
  echo "  MISSING: $dest (looked in: $*)" >&2
  return 1
}

echo "Populating fonts/ from local sources:"
copy_first Roboto-Regular.ttf \
  "$HOME/repos/soundgoof/ESPHomeDesigner/custom_components/esphome_designer/frontend/tests/legacy/.esphome/font/Roboto@400@False@v1.ttf" \
  ".esphome/font/Roboto@400@False@v1.ttf" \
  /usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf
copy_first Roboto-Bold.ttf \
  ".esphome/font/Roboto@700@False@v1.ttf" \
  /usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf
copy_first materialdesignicons-webfont.ttf \
  "$HOME/repos/soundgoof/ESPHomeDesigner/font_ttf/font_ttf/materialdesignicons-webfont.ttf" \
  "$HOME/repos/soundgoof/ESPHomeDesigner/custom_components/esphome_designer/frontend/materialdesignicons-webfont.ttf"
echo "Done."
