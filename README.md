# i3-dotfiles

Personalización de i3 con Polybar y Rofi: tema oscuro con acentos azules,
lanzador de aplicaciones, controles de audio y red, brillo por software,
batería y Pomodoro.

## Requisitos

- Linux con una sesión **i3 sobre X11**; no funciona como tema de GNOME o Wayland.
- i3 4.24 y Polybar 3.7.2 son las versiones comprobadas.
- Polybar con soporte para i3, PulseAudio y red.
- PipeWire/WirePlumber y NetworkManager.
- Fuentes JetBrains Mono y FontAwesome.
- Locale `es_AR.UTF-8` para la fecha en español.

## Instalar

### 1. Instalar las dependencias

En Debian 13:

```bash
sudo apt update
sudo apt install git python3 i3-wm polybar rofi alacritty pavucontrol \
  feh flameshot zenity nautilus network-manager network-manager-gnome \
  xss-lock i3lock dex x11-xserver-utils util-linux pipewire-audio \
  fonts-jetbrains-mono fonts-font-awesome locales-all libglib2.0-bin
```

En otras distribuciones, instalá los paquetes equivalentes antes de continuar.
El instalador comprueba los comandos necesarios y avisa si falta alguno.

### 2. Clonar y aplicar la configuración

```bash
git clone https://github.com/ramirosandoval/i3-dotfiles.git ~/i3-dotfiles
cd ~/i3-dotfiles
python3 install.py
```

El instalador enlaza los archivos del repositorio con `~/.config`, conserva
los archivos ajenos a esta configuración y respalda los reemplazados en
`~/.local/state/i3-dotfiles/backup-*`. Si la validación de i3 falla, restaura
los archivos reemplazados.

**Conservá el repositorio en esa ubicación:** los enlaces apuntan a él.
Editar un archivo enlazado también modifica el archivo del repositorio.

### 3. Activar

Si ya estás en i3, presioná **Super+Shift+R**. Si no, elegí la sesión i3 al
iniciar sesión. El instalador no reinicia el escritorio automáticamente.
`Super` es la tecla Windows en la mayoría de los teclados.

## Actualizar

En cada equipo:

```bash
cd ~/i3-dotfiles
git pull --ff-only
python3 install.py
```

Luego presioná **Super+Shift+R**. Volver a ejecutar el instalador incorpora
los archivos nuevos sin reemplazar los ajustes locales.

## Controles

| Control | Acción |
| --- | --- |
| `Super+Enter` | Abrir Alacritty |
| `Super+D` | Abrir el lanzador de aplicaciones |
| Clic derecho en el lanzador | Seleccionar una ventana |
| `Super+,` o engranaje | Abrir el menú de configuración |
| `Super` + tecla `+` | Silenciar o restaurar el micrófono predeterminado |
| Rueda sobre volumen | Ajustar el volumen |
| Clic sobre volumen | Silenciar o restaurar la salida de audio |
| Clic derecho sobre volumen | Abrir Pavucontrol |
| Clic sobre Ethernet o Wi-Fi | Abrir el selector de conexiones |
| Rueda sobre el sol | Ajustar la atenuación entre 20 % y 100 %, en pasos de 5 % |
| Clic sobre el sol | Restaurar el 100 % |
| Clic izquierdo sobre Pomodoro | Iniciar, pausar o continuar |
| Clic derecho sobre Pomodoro | Reiniciar a 25:00 |

El menú permite configurar audio y micrófono, conexiones, fondo de pantalla,
separación de ventanas y capturas, además de editar o recargar la barra y
bloquear la pantalla.

- **Micrófono:** icono verde cuando está habilitado, tachado rojo cuando está
  silenciado y gris con `?` si no hay una entrada real disponible. Se actualiza
  al cambiar el silencio desde el teclado u otra aplicación.
- **Brillo:** el indicador `% SW` controla atenuación por software, no la
  retroiluminación física. No reduce el consumo de la pantalla y se restablece
  al reiniciar X11.
- **Batería:** muestra icono y porcentaje; indica carga o alimentación externa
  y se pone rojo al bajar a 15 %. Queda vacío en equipos sin batería.
- **Pomodoro:** concentración de 25 minutos, descansos de 5 minutos y uno de
  15 cada cuatro sesiones. Notifica al terminar y deja pausada la siguiente
  etapa. Su estado se guarda en `~/.local/state/polybar-pomodoro/` y se conserva
  al recargar la barra. Las notificaciones requieren un servicio de
  notificaciones activo en la sesión.
- **Teclado:** algunos atajos usan `ñ` y suponen una distribución española.
  Los atajos con flechas también están disponibles.

## Ajustes opcionales por equipo

La configuración detecta las interfaces Ethernet/Wi-Fi y la pantalla activa.
Para el brillo, prefiere la pantalla primaria. La selección de red se hace
al iniciar la barra; recargala si cambiás de interfaz.

Para agregar comandos de inicio propios del equipo, editá
`~/.config/i3/local.conf`. El instalador conserva este archivo y no lo sube
al repositorio. Podés usarlo para programas de inicio, ajustes de pantalla
o un agente de autenticación de privilegios.

Para fijar las interfaces o la pantalla, creá `~/.config/polybar/local.env`
con las variables que necesites:

```sh
ETHERNET_INTERFACE=nombre_de_interfaz_ethernet
WIFI_INTERFACE=nombre_de_interfaz_wifi
BRIGHTNESS_OUTPUT=nombre_de_salida_de_pantalla
```

Reemplazá los valores por los nombres que muestran estos comandos:

```bash
nmcli device
xrandr --listmonitors
```

Si la detección automática funciona, no hace falta crear `local.env`.
Este archivo se ejecuta como shell con tu usuario: usá solo contenido que
hayas revisado. Ni este archivo ni `local.conf` se incluyen en Git.
Los fondos de pantalla y `~/.fehbg` también permanecen locales.

## Restaurar la configuración anterior

El instalador imprime la ubicación del respaldo. Para recuperar un archivo:

1. Quitá su enlace de `~/.config`.
2. Copiá el archivo correspondiente del respaldo a esa misma ubicación.
3. Reiniciá i3 con **Super+Shift+R**.

Los respaldos se conservan al actualizar.

## Comprobar la configuración

Dentro del repositorio, en una sesión X11 con i3 y Rofi instalados:

```bash
python3 check.py
python3 -m unittest discover -s config/polybar -p 'test_*.py'
```

Las pruebas usan directorios temporales y no modifican la configuración
activa ni el brillo. Comprueban scripts, configuración y comportamiento del
instalador; no sustituyen una comprobación manual de teclado, audio y pantalla.
