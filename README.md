# rolplay-server

Reconstrucción por ingeniería inversa del servidor de **Rolplay.net**, un juego de cartas
coleccionables online español (2002-2005) cuyo cliente `RPcliente.exe` 3.9.0 (Visual Basic 6)
dejó de funcionar al cerrar los servidores.

Estado actual: el cliente original hace login contra este servidor, entra al lobby y abre la
ventana de Cartas con barajas, oro y cartas con imagen. Detalle en [docs/ESTADO.md](docs/ESTADO.md)
y formatos en [docs/PROTOCOLO.md](docs/PROTOCOLO.md).

Este repositorio **no** incluye el juego. El instalador original está archivado en
[NinjasCL-archive/rolplay](https://github.com/NinjasCL-archive/rolplay).

## Puesta en marcha

1. Instalar el cliente (`rolplay-3.9.0-installer.exe`) y registrar sus OCX desde una consola elevada:
   ```
   C:\Windows\SysWOW64\regsvr32.exe /s "C:\Program Files (x86)\Rolplay\MSWINSCK.OCX"
   ```
   (y lo mismo para `Mscomctl.ocx`, `MSINET.OCX`, `JwldButn.ocx`, `msdxm.ocx`).
2. Copiar la carpeta del juego a `game/` junto a este repo (o definir `RPCLIENTE` con la ruta del exe).
3. Arrancar el servidor:
   ```
   pip install -r requirements.txt
   python server\rpserver.py
   ```
4. Arrancar el cliente contra localhost:
   ```
   game\RPcliente.exe -local -nocheck
   ```
   Cualquier usuario y contraseña valen por ahora.

## Estructura

| Carpeta | Contenido |
|---|---|
| `server/` | `rpserver.py` (servidor TCP), `handlers.py` (un handler por comando, recarga en caliente), `rp_proto.py` y `table.json` (cifrado y tramas) |
| `tools/` | desensamblado (`funcdump.py`), lectura de vtables del proceso vivo (`vtmap.py`), mapeo comando→handler (`resolve.py`), extracción de la tabla de cifrado (`table_extract.py`), decodificador del `log.log` del cliente |
| `scripts/` | PowerShell para manejar el cliente sin robar el foco (`ui.ps1`) y hacer login automático (`relogin.ps1`) |
| `analysis/` | artefactos del análisis: tabla de objetos VB6, vtables, mapas de despachadores, cadenas del exe, lista de handlers `rcv_*` |
| `docs/` | estado del proyecto y protocolo |

## Cómo añadir un comando

1. Localizar la respuesta en el despachador del formulario (`analysis/dispatchers.json`).
2. Con el cliente abierto: `python tools\vtmap.py` y `python tools\resolve.py Principal 0x7c7be0`.
3. Volcar el handler: `python tools\funcdump.py -b 0x<dirección>` y leer cómo trocea el mensaje
   (`Campo`, `Split`, `InStr`, `Val`).
4. Escribir `h_<COMANDO>` en `server/handlers.py`; el servidor lo recarga en cada mensaje.

## Licencia

MIT para el código de este repositorio. Rolplay.net y sus recursos son obra de David González Bisbal (Sevia).
