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

Mapa completo de Principal y Cartas en `analysis/map_Principal.json` y `analysis/map_Cartas.json`.

## Pendiente de verificar
Salas, partidas, duelos, intercambios, clanes, estadísticas, álbum, compra de sobres.
