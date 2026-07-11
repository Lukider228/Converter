#!/usr/bin/env bash
# Устанавливает Converter в меню приложений: иконка + ярлык с путями
# под текущее расположение проекта.
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
APP_DIR="$HOME/.local/share/applications"

mkdir -p "$ICON_DIR" "$APP_DIR"
cp "$DIR/converter/ui/assets/icon.svg" "$ICON_DIR/converter.svg"

cat > "$APP_DIR/converter.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Converter
Comment=Универсальный конвертер аудио, видео и изображений
Exec="$DIR/run.sh"
Path=$DIR
Icon=converter
Terminal=false
Categories=AudioVideo;AudioVideoEditing;
EOF

update-desktop-database "$APP_DIR" 2>/dev/null || true
echo "Готово: Converter добавлен в меню приложений."
