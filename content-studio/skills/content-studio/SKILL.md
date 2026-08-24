---
name: content-studio
description: Use when producing branded content for clients — writing copy for a brand, generating images or video for a post, building a week or month of pieces, or deciding whether an asset can be generated at all. Also for importing a content plan, filling a pack, or wiring Flow applets.
---

# Producir contenido de marca

Este plugin no escribe el contenido. Decide **qué se puede producir**, con
qué formato, y qué queda pendiente de validar — y arma el paquete que otra
persona va a revisar y aprobar.

La redacción y la generación las hacés vos, o `google-flow`. Lo que aporta
`content-studio` es lo que un generador no tiene por sí solo: la ficha de
cada marca, y la lista de cosas que no hay que producir aunque se puedan.

## Antes de la primera pieza

```
studio_estado          qué pack está activo y sobre qué cartera trabajamos
studio_marca <marca>   ficha, voz, permisos y frases prohibidas
studio_piezas <marca>  a qué id se adjunta el material
```

`studio_marca` no es opcional. La voz es intransferible y es parte del
producto: dos marcas del mismo rubro con el mismo prompt base salen
fundidas, y ése es el modo de falla nativo de un generador.

## Las tres preguntas, en orden

**1. ¿Este asset prueba algo o ilustra un concepto?**

Se generan ilustraciones. No se generan pruebas. Una obra que no se
construyó, un local que no existe, una entrega que no ocurrió o una persona
que no trabaja ahí son afirmaciones falsas sobre el negocio de un cliente —
y el costo lo paga el cliente.

`studio_gate` lo resuelve primero, antes que preset, paleta o aspecto. Si
la respuesta es «prueba», no hay nada más que resolver.

**2. ¿A qué id se adjunta?**

Los ids de pieza son permanentes y de ellos cuelgan los comentarios del
cliente. Uno inventado colisiona de forma irreversible cuando se cargue el
mes real. Si la marca no tiene calendario —que al empezar es lo normal, no
la excepción— el material va a `<marca>/sin-mes/`, sin fecha en el nombre.

**3. ¿Qué de esto hay que validar?**

`studio_revisar` pasa el copy por frases prohibidas, verbos de resultado en
sectores regulados, datos duros y canal de conversión. Corrélo siempre
antes de dar un copy por terminado.

## Reglas que no se negocian

**No se acuñan ids de pieza.** Adjuntar a uno existente, o staging.

**Sin texto dentro de la imagen.** Ni cifras, ni rótulos, ni cotas. Dos
motivos: la generación de glifos es poco confiable, y —más grave— un número
horneado en un pixel esquiva la revisión de copy. Sin esta regla, el gate
de dato sin validar tiene una puerta trasera.

**Ninguna persona identificable sintética presentada como real.** Equipo,
cliente, paciente, docente, profesional. Es derecho de imagen, y en salud
además responsabilidad profesional.

**Ninguna marca, logo, modelo, patente ni packaging de terceros.** Cubre el
riesgo de marca ajena y también el inverso: un producto verosímil pero
inventado se lee como el producto que se vende.

**La ausencia de permiso no es permiso.** Si una marca no tiene declarado
si puede usar trends, humor o tono crudo, se bloquea y se pregunta. No se
hereda de otra marca del mismo cluster: dentro de un mismo cluster conviven
marcas con el permiso dado y marcas con el permiso vedado por escrito.

**Sin identidad visual, la pieza sale marcada `incompleta`.** No se elige
una tipografía ni una paleta plausibles. Una placa que parece terminada
puede llegar a publicarse; una obviamente incompleta, no.

| Racionalización | Realidad |
|---|---|
| «Es sólo un fondo, no hace falta el gate» | El gate cuesta un llamado local. El asset falso cuesta un cliente. |
| «Le pongo el precio que estaba en el brief» | El dato histórico es contexto, no autorización. Va al copy y al pendiente. |
| «Esta marca es parecida a la otra, reuso los hooks» | Es exactamente el par que el gate de vecindad bloquea. |
| «No figura que no pueda usar trends» | No figurar no es permiso. Es un dato faltante. |
| «Genero el logo, después lo cambian» | Una pieza que parece terminada se publica. |
| «Le pongo un id tipo `marca-2026-09-s1-lunes`» | Ese id puede existir mañana y ser otra pieza. Staging. |

## Cuando un gate bloquea

Devuelve un **entregable**, no un error: plan de rodaje, checklist de
autorización, o el dato que falta con quién lo aprueba. Leelo y seguilo.

No reformules el pedido para esquivar el gate. Un rechazo pelado se saltea
reformulando, y el segundo intento es justo el que produce el asset falso.
Si el entregable no alcanza, preguntale al usuario.

## Generar el asset

`content-studio` no genera: prepara y valida. La generación va por
`google-flow` (imagen y video) y `flow-music` (audio), con sus propias
reglas — dryrun antes de un lote, sin paralelizar, sin bajar las pausas.

```
studio_gate       ¿se puede? ¿con qué aspecto?
studio_campos     el prompt sale de la ficha, no de la improvisación
studio_matriz     si es un lote: cuántas variantes son, antes de lanzarlo
  → google-flow   flow_dryrun_recipe, después flow_batch_generate
studio_paquete    copy + manifiesto + pendientes
studio_check      ¿lo entregado se puede medir y tiene procedencia?
```

**No escribas el prompt a mano.** `studio_campos` lo arma desde la ficha de
la marca y le mete adentro las prohibiciones base, así el prompt no se
reinventa en cada pieza. Lo que devuelve es un **borrador**: la ficha manda,
y si un campo la contradice el error está en la traducción, no en la ficha.
Cada campo viene con su origen justamente para poder repasarlo sin abrir la
ficha al lado.

**Antes de un lote, mirá el número.** `studio_matriz` dice cuántas variantes
salen del producto cartesiano. Tres es una prueba; veintiocho es una tarde
de créditos de otra persona. Probá con dos o tres: un lote que falla en la
variante 14 de 28 ya gastó las trece anteriores.

Cada asset generado entra al paquete con su **manifiesto de procedencia**,
que incluye un campo de no-atribución: a qué lugar, obra, caso o persona
ese plano NO puede atribuirse. Es lo que impide que un recurso genérico se
rotule después como algo real, cuando quien monta ya no es quien generó.

## Antes de dar una pieza por terminada

```
studio_check <carpeta del paquete>
```

Falla por tres cosas, todas reales: archivos que no se pueden medir (un PNG
de 0 bytes, un video truncado), manifiesto y disco desincronizados, y assets
sin procedencia. Un asset cuenta como entregado sólo cuando pasa las tres.

No alcanza con que el archivo exista. Un PNG de 0 bytes y uno bueno se ven
igual en un listado, y el que se publica es el que nadie miró.

`studio_check` verifica lo **técnico**: que el archivo se pueda medir, que
el manifiesto y el disco coincidan, que nada esté sin procedencia. Lo
**semántico** —¿esta placa es de esta marca?, ¿esta toma dice lo que el
guión pedía?— no lo puede medir un programa, y no conviene fingir que sí.
Eso lo mira una persona con los `pendientes.md` al lado.

## Applets de Flow

`studio_applet_spec` redacta el pedido de una applet desde un preset del
pack, con el selector de modelo obligatorio incluido. Se pega en el agente
de Flow, y después `studio_applet_descubrir` cablea el `appletId`.

El selector de modelo no es un detalle: cada modelo tiene su cuota diaria y
cuando una se agota el backend contesta `FALLO EN GENERACIÓN` y nada más —
indistinguible de un error transitorio. Sin el desplegable, la reacción
natural es reintentar, que es justo lo que no hay que hacer.

**Después de crear o editar una applet, corré siempre
`studio_applet_verificar`.** El agente de Flow recorta bloques al copiarlos y
reporta el cambio como hecho; el resultado no delata la pérdida, porque las
imágenes salen bien igual hasta que una no. Es una llamada, no gasta nada, y
convierte un recorte silencioso en algo que se ve.

## El prompt se recorta a los 2126 caracteres, y no avisa

Es la trampa más cara de Flow. La imagen vuelve igual, y bien, así que nada
en pantalla dice que se perdió el final.

Acá pesa más que en otros usos por cómo se arma el prompt: las prohibiciones
—sin texto, sin logos, sin terceros, sin personas identificables— van
**últimas**, o sea que son lo primero que se cae. Sin ellas el gate reporta
OK, la pieza vuelve con un rótulo horneado o una cara identificable, y nadie
se entera hasta que el cliente la ve.

`studio_campos` ya lo mide: si el borrador viene con un pendiente de campo
`prompt`, el prompt no entra y hay que acortar la situación antes de
generar. No es un aviso de estilo.

## Los créditos no son el presupuesto de imagen

Medido: corridas que generaron decenas de imágenes informaron costo total 0,
con los archivos en disco. El contador no acompaña la generación de imagen.
Sirve para lo que sí descuenta —video— y para saber que la cuenta está viva.
Leerlo como "lo que va a costar esta tanda" da un número que no significa eso.

## Referencias

- `references/packs.md` — qué va en el core y qué en el pack, y cómo llenarlo
- `references/gates.md` — los diez gates, qué mira cada uno y qué devuelve
