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
Funciona de extremo a extremo: login, lobby (personaje, sala, lista de usuarios, ping) y la ventana
**Cartas** (oro, barajas, listas de cartas con imagen). Los handlers se recargan en caliente.

Comandos con handler: `LOGINUSERADV`, `LOGINUSER`, `LOGOUT`, `GETMSGJOIN`, `GETUSERCHANNEL`, `GETUSERPRIV`,
`GETCOUNTCONN`, `GETUSERINF`, `GETUSERAWAY`, `LSTCONNCNT`, `LSTCONN`, `PINGUSR`, `JOINCHANEL`, `SETUSERPRIV`,
`SETUSERNOPRIV`, `SETUSERAWAY`, `SETUSERNOAWAY`, `MSG`, `GETUSERGOLD`, `GETLSTDECKS`, `GETDECKACT`,
`GETACTCARDLISTCNT`, `GETINACTCARDLISTCNT`, `GETACTCARDLIST`, `GETINACTCARDLIST`.

### Reglas del protocolo que costaron encontrar
- Toda respuesta necesita al menos un argumento (`PINGRPS OK`); si no, "Error en la recepcion de un paquete".
- Las listas terminan **siempre en coma**: el cliente itera `arr(i-1)` y descarta el último elemento.
- Nombres de baraja sin espacios.
- Formatos completos en [PROTOCOLO.md](PROTOCOLO.md).

## Falta

### Corto plazo
- **Catálogo de cartas real**: `cards.csv` del repo NinjasCL y la web [rolplus](https://ninjascl.github.io/rolplus/)
  (coste, ataque, defensa, efectos). Confirmar el significado de los campos 3º, 5º y 6º del ítem de carta
  volcando `0x724280` (función que guarda los campos).
- **Persistencia** (SQLite): usuarios y contraseñas, oro, XP, barajas, colección. Alta de usuario (`ADDUSER`).
- **Salas** (`GETLSTCHANNELS` → Canales 0x785ce0, `SETUSERCHANNEL`) y **chat** (`MSG`, `MSGPRIV`, `JOINPRIV`).
- **Partidas** (`GETGAMELIST` → Partidas 0x7685d0, `CREATEGAME`, `JOINGAME`, `UNJOINGAME`, `SETPLAYERREADY`).

### Medio plazo
- **Duelos** (formulario Torneo, 126 métodos): turnos, ataques, PV, apuestas (`BEGINTURN`, `SENDATTACK`,
  `DEDUCTPV`, `KILLCARD`, `GIRMONS`, `ADDPV`, `SETCATTACK`, `SETCDEFEND`…). Requiere las reglas del juego
  (manual en `version_leeme.txt` del instalador y web rolplus).
- **Intercambios**, **clanes**, **estadísticas**, **álbum**, **compra de sobres** (`BUYCARDS`).
- Multiusuario real: broadcast de `MSGADD`/`LSTCONN`, desconexiones, varios clientes a la vez.

Comandos cliente→servidor sin handler (de `analysis/strings_unicode.txt`): `ADDUSER`, `ADDUSERCLAN`,
`ASKJOINCLAN`, `BUYCARD`, `BUYCARDS`, `CREATECLAN`, `CREATEDEAL`, `CREATEDECK`, `CREATEGAME`, `DEADME`,
`DELETEDECK`, `DEOPUSERCLAN`, `DESTROYCLAN`, `ENDDEAL`, `GETBETCARDLIST`, `GETCARDAGE`, `GETCARDCOUNT`,
`GETCARDCOUNTOPP`, `GETCARDDESC`, `GETCARDESP`, `GETCARDESPF`, `GETCARDHAND`, `GETCARDIMAGE`,
`GETCARDIMAGEMAIN`, `GETCARDNDECK`, `GETCARDPOWER`, `GETCARDPROFILE`, `GETCARDTYPE`, `GETCARDVAL`,
`GETCLANGOLD`, `GETCLANINF`, `GETCLANMEMBERCNT`, `GETCLANMEMBERLST`, `GETCLANSELLCARDLIST`,
`GETCLANSELLPUBLIC`, `GETCLANSELLPUBLICCNT`, `GETDEALFINALRPS`, `GETDEALLIST`, `GETDEALOPP`,
`GETDOIHAVECARD`, `GETDUELBEGINGUS`, `GETDUELCARDLIST`, `GETDUELNUMCARDBET`, `GETDUELNUMCARDBETOPP`,
`GETDUELNUMCARDS`, `GETDUELRES`, `GETGAMELIST`, `GETGAMEOPP`, `GETGAMEOPPLEVEL`, `GETGAMEOPPPV`,
`GETGOLDBET`, `GETGOLDBETOPP`, `GETLSTCARDSEXISTEN`, `GETLSTCARDSLEVELS`, `GETLSTCHANNELS`,
`GETLSTCLANES`, `GETLSTHORD`, `GETLSTSRVADV`, `GETUSERAUTOCAN`, `GETUSERDESC`, `GETUSEREMAIL`,
`GETUSERLEVEL`, `GETUSERLEVELCHANEL`, `GETUSERPASS`, `GIVECLANGOLD`, `INVKADDPV`, `INVKDEDUCTPV`,
`INVKGIRMONS`, `INVKGIRMONSOK`, `INVKREMAMU`, `INVKREMMONS`, `INVKREMPOD`, `ISCREATORCLAN`,
`ISMEMBERCLAN`, `ISMEMBERTHISCLAN`, `ISOPCLAN`, `JOINDEAL`, `JOINGAME`, `JOINPRIV`, `KILLCARD`,
`LEAVECLAN`, `MOVECARD`, `MSGDEAL`, `MSGDEALWARN`, `MSGDUEL`, `MSGGAME`, `MSGPRIV`, `NAMESESSION`,
`OPUSERCLAN`, `REMAMUVAL`, `REMCARDALBUM`, `REMUSERCLAN`, `SELLCARD`, `SENDACTUALPASS`, `SENDATTACK`,
`SENDATTACKRPS`, `SENDENDTURN`, `SETAMUVAL`, `SETCARDACTIVE`, `SETCARDALBUM`, `SETCARDBET`,
`SETCARDINACTIVE`, `SETCATTACK`, `SETCDEFEND`, `SETCLANDESC`, `SETCLANFREE`, `SETCLANMAXMEMBERS`,
`SETCLANSELLCARD`, `SETCLANURL`, `SETCLEANCLANSELLCARD`, `SETDEALIDX`, `SETDECKACT`, `SETGOLDBET`,
`SETINACTIVEDECK`, `SETPINGDEAL`, `SETPINGGAME`, `SETPLAYERACEPT`, `SETPLAYERDREADY`,
`SETPLAYERDUNREADY`, `SETPLAYERNOACEPT`, `SETPLAYERREADY`, `SETPLAYERUNREADY`, `SETREFRESHBET`,
`SETUSERAUTOCAN`, `SETUSERCHANNEL`, `SETUSERDESC`, `SETUSEREMAIL`, `SETUSERPASS`, `SHOWCARDDECK`,
`SHOWCARDIN`, `SHOWCARDOPP`, `SHOWCARDOPPSIT`, `SHOWCARDOUT`, `SHOWCARDUNVEERO`, `SHOWCARDVEER`,
`SHOWGOLDDEALM`, `SHOWGOLDDEALP`, `SHOWKILLCARD`, `SURRENDERME`, `TAKECLANGOLD`, `UNJOINCHANEL`,
`UNJOINDEAL`, `UNJOINGAME`.

## Cómo retomar
1. `python server\rpserver.py` (escucha en 10002; log en `server\server.log`).
2. `game\RPcliente.exe -local -nocheck`, o `powershell scripts\relogin.ps1`.
3. Para un comando nuevo: `python tools\resolve.py Principal 0x7c7be0` (o el despachador del formulario
   que corresponda), volcar el handler con `python tools\funcdump.py -b 0x...` y buscar
   `Campo`/`Split`/`InStr`/`VarTstEq` para deducir el formato. Probar editando `server\handlers.py`
   (se recarga solo) y observando `scripts\ui.ps1` → `Open-Sub 'Cartas' 'c'`, `Read-Cartas`, `Tail-Log`.
