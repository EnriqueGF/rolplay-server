# Protocolo Rolplay.net 3.9.0 (verificado contra el cliente)

## Transporte
- TCP, puerto 10002. Texto ofuscado con una tabla de sustitución por carácter (`server/table.json`):
  letras +2 con wrap (`Y→A`, `Z→B`; excepción `M→0xD1`, `N→O`), espacio → `0xFD`, dígitos → bytes altos.
- Trama: `#` + ENC(payload) + `4CR\xcfPT` + `\r`. Campos separados por espacio. Listas terminan en coma.
- Las respuestas del servidor llevan sufijo `RPS`. Toda respuesta necesita al menos un argumento.
- El cliente recorta `\r`/`\n` finales y trocea por espacios; el primer campo es el comando.

## Login y lobby
| Cliente → servidor | Servidor → cliente |
|---|---|
| `LOGINUSERADV user pass 3.9.0 <PC> <ip> <puerto> WindowsNT 6.2 9200` | `LOGINUSERRPS OK-<sessionid>` |
| `GETMSGJOIN <sid>` | `GETMSGJOINRPS <texto de bienvenida>` |
| `GETUSERCHANNEL <sid>` | `GETUSERCHANNELRPS Principiantes 1(n1-n5)` |
| `GETUSERPRIV user` | `GETUSERPRIVRPS 1` |
| `GETCOUNTCONN user` | `GETCOUNTCONNRPS <online> 0` |
| `GETUSERINF user` | `GETUSERINFRPS nivel xp ? ? ? ? ?` (`1 0 0 0 0 0 2` en el log original; la UI muestra nivel, XP, vida 20, oro, stat, partidas 0/0) |
| `JOINCHANEL <sid> <sala>` | (sin respuesta) |
| `GETUSERAWAY user` | `GETUSERAWAYRPS 0` |
| `LSTCONNCNT user <sala>` | `LSTCONNCNTRPS <n>` |
| `LSTCONN user <sala> 0 35` | `LSTCONNRPS  user1(1) ,user2(1) ,` |
| `SETUSERPRIV <sid> <sala>` | (sin respuesta) |
| `PINGUSR user` | `PINGRPS OK` |
| `MSG …` | broadcast `MSG user texto` (formato exacto pendiente de verificar) |

Otros mensajes servidor→cliente vistos en el log original: `MSGADD <user>(1)  se ha unido a la Sala de Retos @ADD@`.

## Ventana Cartas
| Cliente → servidor | Servidor → cliente |
|---|---|
| `GETUSERGOLD user` | `GETUSERGOLDRPS <oro>` |
| `GETLSTDECKS user N` (N=0 reserva, 1 activa) | `GETLSTDECKSRPS baraja1,baraja2, N` |
| `GETDECKACT user N` | `GETDECKACTRPS <baraja> N` |
| `GETACTCARDLISTCNT user baraja` | `GETACTCARDLISTCNTRPS <total> 0` |
| `GETINACTCARDLISTCNT user baraja` | `GETINACTCARDLISTCNTRPS <total> 0` |
| `GETACTCARDLIST user <from> <from> 20` | `GETACTCARDLISTRPS item,item, COL:<n>` |
| `GETINACTCARDLIST user <from> <from> 20` | `GETINACTCARDLISTRPS item,item, COL:<n>` |

Ítem de carta: `nombre:id:int:imagen.jpg:int:str` (f1 = id numérico único, f3 = fichero en `imagenes\`,
por ejemplo `crt_elfo_bardo.jpg`). `<n>` = cartas recibidas hasta ahora; el cliente pide páginas de 20
hasta alcanzar `<total>`. Un ítem que el cliente no consigue procesar (p. ej. imagen inexistente)
hace que repita la petición indefinidamente.

## Salas y Canales
| Cliente → servidor | Servidor → cliente |
|---|---|
| `GETLSTCHANNELS <sid>` | `GETLSTCHANNELSRPS canal1,canal2,canal3,` |
| `SETUSERCHANNEL <sid> <sala>` | `SETUSERCHANNELRPS <sala>` |

## Retos y Partidas
| Cliente → servidor | Servidor → cliente |
|---|---|
| `GETGAMELIST <user>` | `GETGAMELISTRPS Sin partidas activas` (o `partida@creador=descripcion,`) |
| `CREATEGAME <nombre> <pass> <oro> <cartas> <baraja>` | `CREATEGAMERPS OK <id>` |
| `JOINGAME <id> <pass>` | `JOINGAMERPS OK` |
| `UNJOINGAME` | `UNJOINGAMERPS OK` |

## Chat y Mensajería
| Cliente → servidor | Servidor → cliente |
|---|---|
| `MSG <sid> <texto_con_espacios_como_=> <sala>` | broadcast `MSG <usuario> <texto_limpio>` a los usuarios en la misma sala |
| `MSGPRIV <destinatario> <texto>` | `MSGPRIV <remitente> <texto>` al destinatario |

## Handlers resueltos (dirección real en el exe)
| Respuesta | Formulario | Función |
|---|---|---|
| `GETUSERINFRPS` | Principal | 0x7182d0 |
| `LSTCONNRPS` | Principal | 0x710780 |
| `GETMSGJOINRPS` | Principal | 0x712430 |
| `GETUSERCHANNELRPS` | Principal | 0x7141e0 |
| `GETUSERGOLDRPS` | Cartas / Principal | 0x7613d0 / 0x711510 |
| `GETLSTDECKSRPS` | Cartas / Barajas | 0x765810 / 0x7bb7c0 |
| `GETDECKACTRPS` | Cartas | 0x765480 |
| `GETINACTCARDLISTCNTRPS` | Cartas | 0x764e40 |
| `GETINACTCARDLISTRPS` | Cartas | 0x7624f0 |
| `GETACTCARDLISTRPS` | Cartas | 0x7634e0 |
| `GETLSTCHANNELSRPS` | Canales | 0x785ce0 |
| `GETGAMELISTRPS` | Partidas | 0x7685d0 |
| `GETCARDHANDRPS` | Torneo | 0x7365e0 |
| `SHOWCARDOPPACT` | Torneo | 0x73e960 |
| `SHOWCARDOPPSITACT` | Torneo | 0x73fa90 |
| `SHOWCARDVEERACT` | Torneo | 0x741000 |
| `SHOWCARDUNVEERACT` | Torneo | 0x742070 |
| `DEDUCTPV` | Torneo | 0x73d4b0 |
| `DEDUCTPVOPP` | Torneo | 0x742250 |
| `KILLCARD` | Torneo | 0x73dcb0 |
| `KILLCARDOPP` | Torneo | 0x7427b0 |
| `DEADPLAYER` | Torneo | 0x73e5b0 |
| `GETDUELRESRPS` | Torneo_res | 0x751a80 |

## Duelos y Torneo (Formulario Torneo.frm)
| Cliente → servidor | Servidor → cliente | Descripción |
|---|---|---|
| `GETUSERLEVEL <user>` | `GETUSERLEVELRPS <lvl>` | Nivel del jugador |
| `GETDUELNUMCARDS <user> <opp>` | `GETDUELNUMCARDSRPS 8` | Tamaño de mano inicial (8 cartas) |
| `GETDUELBEGINGUS <user> <opp>` | `GETDUELBEGINGUSRPS <1|2>` | Jugador que empieza el turno |
| `GETGAMEOPP <user> <opp>` | `GETGAMEOPPRPS <opp>` | Nombre del rival |
| `GETGAMEOPPLEVEL <user> <opp>` | `GETGAMEOPPLEVELRPS <lvl>` | Nivel del rival |
| `GETGAMEOPPPV <user> <opp>` | `GETGAMEOPPPVRPS <pv>` | Puntos de vida del rival (20) |
| `GETGOLDBET <user> <opp>` | `GETGOLDBETRPS <oro>` | Oro apostado |
| `SETPLAYERREADY <user> <opp>` | `SETGAMEREADY OK` | Marca preparado para iniciar |
| `GETCARDCOUNT <user> <opp>` | `GETCARDCOUNTRPS <n>` [`BEGINTURN OK`] | Cartas restantes en mazo |
| `GETCARDHAND <user>` | `GETCARDHANDRPS <slot> <id> <img.jpg> <lvl> <tipo> ...` | Robar carta formateada |
| `SENDACTUALPASS <user> <opp> <1..6>` | `SENDACTUALPASS <fase>` | Paso de fase (1=Degirar, 2=Robar, 3=Poder, 4=Criatura, 5=Amuleto, 6=Ataque) |
| `SHOWCARDOPP <slot> <tipo>` | `SHOWCARDOPPACT <slot> <tipo> ...` | Jugar Poder o Invocar Criatura |
| `SHOWCARDVEER <slot>` | `SHOWCARDVEERACT <slot>` | Girar carta (atacar) |
| `SHOWCARDUNVEERO` | `SHOWCARDUNVEERACT OK` | Degirar todas las cartas |
| `SETCATTACK <slot>` | `SETCATTACKRPS OK` | Declarar criatura atacante |
| `SETCDEFEND <def_slot> <att_slot>` | `SETCDEFENDRPS OK` | Declarar criatura defensora |
| `SENDATTACK <slot>` | (resolución de combate) | Ejecutar ataque |
| `INVKDEDUCTPV <dmg>` | `DEDUCTPVOPP <dmg>` (y `DEDUCTPV <dmg>` al rival) | Deducir vida |
| `SETAMUVAL <user> <efecto> <val>` | `SETAMUVALRPS OK` | Aplicar efecto de amuleto (ataque, defensa, pv_turno, rem_mons, gir_mons) |
| `SENDENDTURN` | `BEGINTURN OK` y `SENDACTUALPASS 1` al rival | Pasar turno |
| `SURRENDERME <user> <opp>` | `DEADPLAYER SURRENDER` | Rendición |
| `GETDUELRES <user> <opp>` | `GETDUELRESRPS <mins> <rival> <xp> <oro>` | Resultados y recompensas |

## Pendiente de verificar
Intercambios multijugador directos, clanes avanzados y tienda de sobres.

