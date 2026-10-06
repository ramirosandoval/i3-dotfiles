#!/bin/sh
set -eu
choice=$(printf '%s\n' 'Audio y micrófono' 'Conexiones de red' 'Explorar archivos' 'Elegir fondo de pantalla' 'Captura de pantalla' 'Ventanas sin separación' 'Ventanas con separación' 'Editar configuración de Polybar' 'Recargar barra' 'Bloquear pantalla' | rofi -dmenu -i -no-custom -p 'Configuración') || exit 0
case "$choice" in
    'Audio y micrófono') exec pavucontrol ;;
    'Conexiones de red') exec nm-connection-editor ;;
    'Explorar archivos') exec nautilus --new-window ;;
    'Elegir fondo de pantalla')
        image=$(zenity --file-selection --title='Elegir fondo de pantalla' --file-filter='Imágenes | *.png *.jpg *.jpeg *.webp') || exit 0
        [ -f "$image" ] && exec feh --bg-fill -- "$image"
        ;;
    'Captura de pantalla') exec flameshot gui ;;
    'Ventanas sin separación') exec i3-msg 'gaps inner current set 0; gaps outer current set 0' ;;
    'Ventanas con separación') exec i3-msg 'gaps inner current set 10; gaps outer current set 4' ;;
    'Editar configuración de Polybar') exec xdg-open "$HOME/.config/polybar/config.ini" ;;
    'Recargar barra') exec "$HOME/.config/polybar/launch.sh" ;;
    'Bloquear pantalla') exec loginctl lock-session ;;
esac
