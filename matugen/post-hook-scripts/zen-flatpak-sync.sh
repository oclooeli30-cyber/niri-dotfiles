#!/usr/bin/env bash
set -e

ZEN_DIR="$HOME/.var/app/app.zen_browser.zen"

# Copy GTK3 colors
mkdir -p "$ZEN_DIR/config/gtk-3.0"
cp "$HOME/.config/gtk-3.0/colors.css" "$ZEN_DIR/config/gtk-3.0/colors.css" 2>/dev/null || true
cp "$HOME/.config/gtk-3.0/gtk.css" "$ZEN_DIR/config/gtk-3.0/gtk.css" 2>/dev/null || true
cp "$HOME/.config/gtk-3.0/settings.ini" "$ZEN_DIR/config/gtk-3.0/settings.ini" 2>/dev/null || true

# Copy GTK4 colors
mkdir -p "$ZEN_DIR/config/gtk-4.0"
cp "$HOME/.config/gtk-4.0/colors.css" "$ZEN_DIR/config/gtk-4.0/colors.css" 2>/dev/null || true
cp "$HOME/.config/gtk-4.0/gtk.css" "$ZEN_DIR/config/gtk-4.0/gtk.css" 2>/dev/null || true

# Set dark color scheme inside Flatpak sandbox
flatpak run --command=sh app.zen_browser.zen -c \
    "gsettings set org.gnome.desktop.interface color-scheme prefer-dark 2>/dev/null" 2>/dev/null || true

# Also copy caffyne style colors for compatibility
cp "$HOME/.config/caffyne-shell/style/colors.css" "$ZEN_DIR/config/caffyne-shell/style/colors.css" 2>/dev/null || true

exit 0
