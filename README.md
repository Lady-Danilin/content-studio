# content-studio

Plugin de Claude Code para producir contenido de marca en una agencia: del
plan de contenidos a la pieza entregable.

Lo que aporta no es generar —eso ya lo hacen otras herramientas— sino saber
**qué no hay que generar**. Una obra que todavía no se construyó, un local
que no existe, una entrega que no ocurrió, una persona que no trabaja ahí, o
un precio que nadie confirmó son afirmaciones falsas sobre el negocio de un
cliente. El costo lo paga el cliente, no la agencia.

Cuando algo no se puede producir, el plugin devuelve el camino correcto —un
plan de rodaje, una checklist de autorización, el dato que falta y quién lo
aprueba— en vez de un error. Un rechazo pelado se esquiva reformulando el
pedido, y el segundo intento es justo el que produce el asset falso.

## Instalación

```
/plugin marketplace add Lady-Danilin/content-studio
/plugin install content-studio@content-studio
```

Verificá con:

```bash
python3 ~/.claude/plugins/marketplaces/content-studio/content-studio/doctor.py
```

El plugin queda instalado **sin ninguna cartera**: sin un pack no hay marcas,
ni voz, ni calendario, y el doctor lo dice. El pack de tu agencia va a
`~/.config/content-studio/packs/<nombre>/`, fuera de git —cómo armarlo está
en [`packs/README.md`](./content-studio/packs/README.md)—. Para ver el plugin
funcionando antes de tener el tuyo:

```bash
STUDIO_PACK_NAME=_ejemplo python3 ~/.claude/plugins/marketplaces/content-studio/content-studio/doctor.py
```

Para generar imagen, video o música hace falta además el marketplace
[`media_plugins`](https://github.com/Montinou/media_plugins):

```
/plugin marketplace add Montinou/media_plugins
/plugin install google-flow@media-plugins      # imagen y video
/plugin install flow-music@media-plugins       # audio
```

`content-studio` funciona sin ellos: prepara, valida y arma el paquete. Los
necesita sólo para generar el material.

## Cómo se usa

```
/studio-setup           puesta a punto y estado del plan
/studio-importar        traer un plan de contenidos existente
/studio-huecos          qué falta para poder producir sin inventar nada
/studio-pieza           producir una pieza, del guión al paquete
```

Un ciclo típico:

```
studio_marca      la ficha, la voz, los permisos, las frases prohibidas
studio_piezas     a qué id se adjunta el material
studio_gate       ¿este asset se puede generar? ¿con qué aspecto?
  → google-flow   generar, con dryrun antes de cualquier lote
studio_revisar    el copy final contra todos los gates de texto
studio_paquete    copy + manifiesto + pendientes
```

## Qué produce

```
studio-out/<marca>/<id-de-pieza>/
├── copy.md            el texto, listo para revisar
├── manifiesto.json    procedencia de cada asset y su no-atribución
├── pendientes.md      qué falta validar, con quién y por qué
├── work/              el proceso: intermedios, descartes, versiones
└── assets/            lo que se entrega
```

`pendientes.md` es lo que hace útil al resto: un paquete sin él se lee como
aprobado.

`work/` y `assets/` no son lo mismo, y confundirlos es el error caro.
`work/` se puede tirar. Un archivo se gana entrar a `assets/` **por estar
medido**, no por haber sido generado: un PNG de 0 bytes y uno bueno se ven
igual en un listado de archivos.

`studio_check` mide de verdad —dimensiones por encabezado, duración por
`ffprobe`— y falla por tres cosas: archivos no medibles, manifiesto y disco
desincronizados, y assets sin procedencia. Un asset cuenta como entregado
sólo cuando pasa las tres.

El **manifiesto** lleva un campo de no-atribución que nombra a qué lugar,
obra, caso o persona ese plano no puede atribuirse. Es lo que impide que un
recurso genérico se rotule después como algo real, cuando quien monta ya no
es quien generó.

## Los gates

| Gate | Bloquea cuando |
|---|---|
| `probatorio` | El asset afirma un hecho en vez de ilustrar un concepto |
| `dato_sin_validar` | Una cifra no aparece en ninguna fuente del plan |
| `sector_regulado` | Una marca de salud o financiera afirma un resultado |
| `blocklist` | Aparece una frase que el cliente prohibió |
| `identidad_visual` | Nunca: marca la pieza `incompleta` |
| `vecindad` | Se reusa la voz de una marca en otra parecida |
| `just_in_time` | Se pre-produce un slot de tendencia fuera de su ventana |
| `terceros_y_personas` | Hay marca ajena o persona identificable sintética |
| `sin_texto` | Se pide texto o cifras dentro de la imagen |
| `conversion` | Falta el canal o la palabra clave del CTA |

Ninguno se puede apagar desde un pack. Un pack les aporta datos —qué frases
prohibió un cliente, qué marcas se parecen— pero no puede desactivarlos: si
se pudiera, la única protección real dependería de que alguien se acuerde de
escribirla.

El detalle de cada uno está en
[`skills/content-studio/references/gates.md`](./content-studio/skills/content-studio/references/gates.md).

## Core y packs

| Capa | Qué vive ahí | ¿Le sirve a cualquiera? |
|---|---|---|
| **core** — `lib/`, `mcp/`, `skills/`, `commands/` | los gates, el contrato de formato, el manifiesto, el armado del paquete | **sí** |
| **pack** — `packs/<agencia>/` | marcas, voz, presets, frases prohibidas, palabras clave | **no**, es de esa agencia |

**Si otra agencia no lo puede usar tal cual, es pack.** El core tiene que
funcionar sin ningún pack: un pack agrega atajos, no capacidades.

Los packs reales viven en `~/.config/content-studio/packs/`, **fuera de
git**. Un pack contiene direcciones, teléfonos, aranceles, nombres de
profesionales con matrícula y qué puede y no puede decir cada cuenta:
publicarlo expone a los clientes, no a la agencia.

Este repositorio es público y no incluye ningún pack real. El único que
viaja es [`_ejemplo`](./content-studio/packs/_ejemplo), con dos marcas
inventadas — elegidas para que se disparen los gates que importan.

## Qué tan genérico es

El core no trae ninguna marca, ningún cliente ni ninguna agencia adentro, y
eso está verificado: `lib/`, `mcp/`, `hooks/`, `commands/` y `skills/` no
mencionan un solo cliente real. Tampoco impone una taxonomía de contenido —
`atrae/demuestra/convierte` aparece en la documentación, no en una
validación. Cualquier agencia puede instalarlo y armar su pack.

Pero conviene saber en qué **no** es neutral, porque los supuestos que no se
declaran se descubren tarde:

| Eje | Estado |
|---|---|
| Agencia y clientes | **agnóstico** — todo vive en el pack |
| Taxonomía de funciones | **agnóstico** — no hay enum cerrado |
| Formato de id de pieza | configurable con `convenciones.re_id_pieza` |
| Techo del prompt | configurable con `convenciones.techo_prompt` |
| **Idioma** | **español**, y afecta a tres gates |
| **Plataformas** | redes sociales: reel, historia, feed, carrusel, placa, ads, YouTube, LinkedIn. No hay email, print ni web |

El idioma es el que más importa. Los gates de `dato_sin_validar`,
`sector_regulado` y `probatorio` son expresiones regulares sobre texto en
español. Con contenido en otro idioma **no fallan: devuelven OK**, que es
peor. Medido: «The treatment eliminates the pain» pasa como aviso donde su
equivalente en español bloquea — una promesa clínica que se escapa.

Mientras haya un solo juego de patrones, lo honesto es declararlo y avisar.
Un pack puede poner `"idioma": "en"` y el plugin lo dice al arrancar, en
`studio_estado`, en el doctor y en cada `studio_revisar`. Traducir
`PATRONES_DATO`, `VERBOS_RESULTADO` e `INDICIOS_PROBATORIOS` en
`lib/gates.py` es lo que hace falta para soportar otro idioma de verdad.

## Requisitos

`python3` y nada más. El servidor MCP habla JSON-RPC sobre stdio usando sólo
la stdlib, a propósito: el Python de Homebrew está bajo PEP 668 e instalar
dependencias forzaría `--break-system-packages` sobre el intérprete del
sistema.

Para las herramientas de applets hacen falta además las cookies de
labs.google, que se leen de `~/.config/google-flow/` — el mismo archivo que
ya usa `google-flow`, así que no hay que exportar dos veces.

## Documentación

- [`content-studio/README.md`](./content-studio/README.md) — el plugin en detalle
- [`content-studio/CONFIG.md`](./content-studio/CONFIG.md) — variables de entorno
- [`content-studio/packs/README.md`](./content-studio/packs/README.md) — armar un pack
- [`content-studio/skills/content-studio/SKILL.md`](./content-studio/skills/content-studio/SKILL.md) — cómo se opera

## Licencia

MIT.
