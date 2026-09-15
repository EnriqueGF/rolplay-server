# Estado del proyecto

Última actualización: 2026-09-15.

## Objetivo

Recrear el servidor del juego de cartas online **Rolplay.net** (2002-2005, cliente 3.9.0) a partir
del cliente original `RPcliente.exe`, para que vuelva a funcionar contra un servidor propio.

## Hecho

### Instalación y entorno
- El instalador `rpcliente_windows_3_9_0.exe` que teníamos estaba **corrupto** (256 KB a ceros cada 1 MB).
  Copia íntegra: [NinjasCL-archive/rolplay](https://github.com/NinjasCL-archive/rolplay) (`rolplay-3.9.0-installer.exe`).
- El instalador es install4j (Java) pero el juego es **Visual Basic 6 nativo** con `MSWINSCK.OCX`.
  No hay descompilación a fuente: el trabajo es desensamblado más captura de tráfico.
- Los OCX hay que registrarlos con `SysWOW64\regsvr32.exe` elevado (`MSWINSCK`, `Mscomctl`, `MSINET`, `JwldButn`, `msdxm`).
- El cliente admite `-local` (conecta a localhost:10002) y `-nocheck` (sin comprobación de versión por FTP).
  Alternativa: editar `winsock_host.dat` (`login 127.0.0.1 10002`).
- Servidor original: `80.26.94.33:10002`. Actualizaciones por `ftp://www.rolplay.net`.

### Ingeniería inversa
- **Cifrado**: tabla de sustitución por carácter (`Encriptar` 0x7205f0 / `Desencriptar` 0x71eaf0),
  extraída completa a `server/table.json` con `tools/table_extract.py`.
- **Trama**: `#` + payload cifrado + `4CR\xcfPT` + `\r`. Varias tramas pueden llegar en un mismo segmento TCP.
- El PDB que trae el instalador no corresponde a este binario. `analysis/RPcliente.clu` lista todos los
  handlers `rcv_*` del cliente (fichero del ofuscador con el que se compiló).
- **Despachadores** por formulario (comparan el comando y llaman `[vtable+off]`):
  Principal 0x7c7be0, Cartas 0x7be700, Intercambio 0x7782d0 (lista completa en `analysis/dispatchers.json`).
- Las vtables de los formularios VB6 se rellenan **en tiempo de ejecución** en `.data`; se leen de la
  memoria del proceso (`tools/vtmap.py`) y `tools/resolve.py` mapea comando → función `rcv_*` real.
  Las entradas `GetMem*/PutMem*` son variables públicas, no métodos.
- Helper `Campo(msg, n)` = 0x721fe0 (campo n separado por espacios; 1 = comando).

### Servidor (`server/`)
Funciona con persistencia SQLite completa (`server/rolplay.db`), catálogo real de 285 cartas importado
de `cards.csv` con imágenes verificadas en `game/imagenes/crt_*.jpg`, gestión de barajas (activas y reserva),
salas/canales, partidas/retos y chat en tiempo real. Los handlers se recargan en caliente.

Comandos con handler implementado: `LOGINUSERADV`, `LOGINUSER`, `LOGOUT`, `GETMSGJOIN`, `GETUSERCHANNEL`, `GETUSERPRIV`,
`GETCOUNTCONN`, `GETUSERINF`, `GETUSERLEVEL`, `GETUSERXP`, `GETUSERAWAY`, `LSTCONNCNT`, `LSTCONN`, `PINGUSR`,
`JOINCHANEL`, `SETUSERCHANNEL`, `GETLSTCHANNELS`, `SETUSERPRIV`, `SETUSERNOPRIV`, `SETUSERAWAY`, `SETUSERNOAWAY`,
`MSG`, `MSGPRIV`, `GETUSERGOLD`, `GETLSTDECKS`, `GETDECKACT`, `SETDECKACT`, `CREATEDECK`, `DELETEDECK`,
`GETACTCARDLISTCNT`, `GETINACTCARDLISTCNT`, `GETACTCARDLIST`, `GETINACTCARDLIST`, `GETGAMELIST`, `CREATEGAME`,
`JOINGAME`, `UNJOINGAME`, `GETDEALLIST`, `GETLSTCLANES`, `EST`, `GETCARDIMAGEMAIN`.

### Driver de Automatización (`tools/rp_driver.py`)
Harness completo en Python para lanzar, autenticar, navegar y leer el estado de la interfaz de usuario
de forma totalmente programática, **sin necesidad de capturas de pantalla** ni confirmación del usuario:
- Conexión al escritorio interactivo de Windows (`Default` en WinSta0) con soporte de tipos 64 bits.
- Lanzamiento desacoplado mediante WMI (`Win32_Process.Create`) para sobrevivir a la sesión del agente.
- Autenticación automática (`login`).
- Navegación fiable a subventanas (`nav cartas`, `nav salas`, `nav retos`, etc.) mediante cálculo de
  coordenadas relativas y eventos de ratón Win32 reales sobre botones JwldButn.
- Volcado estructurado del estado de controles (TextBox, CheckBox, ComboBox, ListBox, TreeView) en JSON (`status` / `read`).
- Cierre automático de subventanas modales (`close`).
- Envío de mensajes al chat del lobby (`chat <msg>`).
- Suite de pruebas completa (`test`) que ejecuta el recorrido automatizado por todas las pantallas.

### Reglas del protocolo verificadas
- Toda respuesta necesita al menos un argumento (`PINGRPS OK`); si no, "Error en la recepcion de un paquete".
- Las listas terminan **siempre en coma**: el cliente itera `arr(i-1)` y descarta el último elemento.
- Nombres de baraja sin espacios.
- Salas: `GETLSTCHANNELSRPS <canal1>,<canal2>,...`
- Partidas: Si no hay, `GETGAMELISTRPS Sin partidas activas`. Si hay: `nombre@creador=descripcion,`.
- Chat: `MSG <usuario> <texto>`.
- Formatos completos en [PROTOCOLO.md](PROTOCOLO.md).

## Siguiente Fase
- **Combate / Duelos (Formulario Torneo)**: motor de juego por turnos, manos iniciales, invocaciones (`GIRMONS`, `INVKREMMONS`),
  puntos de vida (`ADDPV`, `DEDUCTPV`), apuestas de oro y cartas, y resolución de victoria/derrota.
- **Intercambios y Clanes**: completar los flujos multijugador específicos entre 2 clientes simultáneos.

