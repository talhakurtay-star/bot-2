#!/usr/bin/env bash
# Masaustune 'Jarvis' kisayolu olusturur (macOS / Linux)
cd "$(dirname "$0")"
DIR="$(pwd)"
DESK="$HOME/Desktop"
mkdir -p "$DESK"
chmod +x "$DIR/baslat.command"

if [ "$(uname)" = "Darwin" ]; then
  ln -sf "$DIR/baslat.command" "$DESK/Jarvis.command"
  echo "Masaustune 'Jarvis.command' eklendi. Cift tiklayarak calistir."
  echo "(Ikon: assets/jarvis.png - istersen Get Info ile elle atayabilirsin.)"
else
  cat > "$DESK/Jarvis.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Jarvis
Comment=Jarvis sesli asistan
Exec=bash "$DIR/baslat.command"
Icon=$DIR/assets/jarvis.png
Terminal=true
Categories=Utility;
EOF
  chmod +x "$DESK/Jarvis.desktop"
  echo "Masaustune 'Jarvis' kisayolu eklendi."
fi
read -p "Enter ile kapat..." _
