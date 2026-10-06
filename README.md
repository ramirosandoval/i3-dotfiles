# i3-dotfiles

Configuración compartida de i3, Polybar y Rofi: tema oscuro/azul, atajos,
menú de configuración, volumen, red y atenuación de pantalla por software.
Sin claves SSH, contraseñas, IP privadas ni configuraciones de servicios personales.

## Instalar en otra PC

Base verificada: Debian 13, sesión **i3 sobre X11**, i3 4.24, Polybar 3.7.2
con soporte i3/PulseAudio/network y PipeWire/WirePlumber.
No es una configuración para GNOME ni Wayland.

En Debian 13:

```bash
sudo apt update
sudo apt install git python3 i3-wm polybar rofi alacritty pavucontrol \
  feh flameshot zenity nautilus network-manager network-manager-gnome \
  xss-lock i3lock dex x11-xserver-utils util-linux pipewire-audio \
  fonts-jetbrains-mono fonts-font-awesome
```

El repositorio es privado: primero autorizá tu cuenta GitHub en ese equipo.
No copies claves privadas de otra PC.

```bash
git clone git@github.com:ramirosandoval/i3-dotfiles.git ~/i3-dotfiles
cd ~/i3-dotfiles
python3 install.py
```

Si ya estás en i3, presioná **Super+Shift+R**; si no, elegí la sesión i3
al iniciar sesión. El instalador no reinicia tu escritorio automáticamente.

El instalador enlaza **archivos individuales**, conserva otros archivos y
respalda lo reemplazado en `~/.local/state/i3-dotfiles/backup-*`.
Si la validación de i3 falla, restaura los archivos reemplazados.
No muevas ni borres el clon después de instalar: los enlaces apuntan a él.

## Actualizar todas las PCs

En cada equipo, dentro de su clon:

```bash
git pull --ff-only
python3 install.py
```

Luego **Super+Shift+R**. Los enlaces reciben cambios de Git directamente;
volver a ejecutar el instalador incorpora también archivos nuevos.
Editar los archivos enlazados edita el clon: revisá `git diff` antes de commitear.

## Ajustes locales por equipo

El instalador conserva o crea `~/.config/i3/local.conf`. No se sube a Git.
Usalo para resoluciones, programas propios del equipo y agentes de autenticación.
Ejemplo para la PC original, **solo si estos comandos existen y los necesitás**:

```i3
exec --no-startup-id xrandr --output HDMI-A-0 --mode 1920x1080
exec --no-startup-id systemctl --user restart input-leap-server
```

En la laptop no hace falta forzar la pantalla a la resolución de la PC.
El antiguo comando del agente Polkit de esta PC no se incluyó porque su ruta
no existe en los equipos revisados. Si necesitás un agente para diálogos de
privilegios, instalá uno y agregá su comando a `local.conf` (por ejemplo
`lxpolkit`, paquete `lxpolkit` en Debian 13).

Polybar elige una interfaz Ethernet/Wi-Fi conectada; si está desconectado,
usa la primera interfaz física administrada. Ignora bridges y VPN.
La selección se hace al arrancar la barra: recargala al cambiar de interfaz.
El brillo usa la pantalla primaria activa, o la primera activa si no hay primaria.
Podés fijar ambos en `~/.config/polybar/local.env`, fuera de Git:

```sh
NETWORK_INTERFACE=enp1s0
BRIGHTNESS_OUTPUT=eDP-1
```

Estos nombres son ejemplos: consultá `nmcli device` y `xrandr --listmonitors`.
El archivo `local.env` se ejecuta como código shell de tu usuario: no uses
archivos de terceros que no hayas revisado.

## Controles

- **Super+Enter**: Alacritty.
- **Super+D**: aplicaciones; clic derecho en el lanzador: ventanas.
- **Super+,** o engranaje: audio/micrófono, red, archivos, fondo,
  capturas, separación de ventanas, editar configuración, recargar y bloquear.
- **Super++**: silenciar/restaurar el micrófono predeterminado.
- **Volumen**: rueda ajusta; clic silencia; clic derecho abre Pavucontrol.
- **Sol / `% SW`**: rueda ajusta en pasos de 5%, entre 20% y 100%;
  clic vuelve a 100%. Es atenuación por software, **no retroiluminación física**;
  no reduce el consumo de la pantalla y no persiste después de reiniciar X11.
- Se conservan los atajos de escritorios, movimiento, resize y bloqueo.
  Los atajos con `ñ` suponen teclado español; las flechas siguen disponibles.

Un solo panel Polybar; no se añade batería, control DDC ni panel por monitor.
El tema no repara drivers/audio: si aparece Dummy Output, diagnosticá
PipeWire/WirePlumber antes de atribuirlo a los atajos.

## Comprobar y recuperar

Dentro de una sesión X11 con i3 y Rofi instalados:

```bash
python3 check.py
```

Comprueba selección de pantalla, brillo, rutas del menú, shell, configuración
real de i3/Rofi, respaldos, instalación repetida y recuperación ante error.
Usa directorios temporales; no modifica la configuración activa ni el brillo.
No demuestra pulsaciones físicas de teclado ni sonido audible.

Para restaurar un archivo, reemplazá su enlace por la copia correspondiente
al respaldo que imprimió el instalador y reiniciá i3. Los respaldos no se borran
al actualizar. Fondos de pantalla y `~/.fehbg` permanecen locales.
