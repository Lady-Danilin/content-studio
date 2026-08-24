# Los gates

Cada uno devuelve `{gate, estado, hallazgos, entregable}` con estado `ok`,
`aviso` o `bloqueo`. Un solo bloqueo frena; los avisos no frenan pero viajan
enteros a `pendientes.md`.

Ninguno se puede apagar desde un pack. Un pack les aporta datos —qué frases
prohibió un cliente, qué marcas se parecen— pero no puede desactivarlos: si
se pudiera, la única protección real dependería de que alguien se acuerde
de escribirla.

| Gate | Qué mira | Bloquea cuando |
|---|---|---|
| `probatorio` | Si el asset afirma un hecho o ilustra un concepto | La función es `prueba`, o no se declaró |
| `dato_sin_validar` | Precio, cuota, tasa, plazo, stock, dosis, especificación, contacto | El dato no aparece en ninguna fuente |
| `sector_regulado` | Verbos de resultado en indicativo | La marca es regulada y el texto afirma un resultado |
| `blocklist` | Frases que el cliente prohibió | Aparece una, aunque sea citada |
| `identidad_visual` | Logo, paleta, tipografía | Nunca: avisa y marca la pieza `incompleta` |
| `vecindad` | Reuso de voz entre marcas parecidas | El par está declarado como peligroso |
| `just_in_time` | Slots atados a un trend o a un stock del día | Falta más tiempo que la ventana |
| `terceros_y_personas` | Marcas ajenas y personas identificables | Aparece cualquiera de las dos |
| `sin_texto` | Texto o cifras dentro de la imagen | El pedido incluye texto a renderizar |
| `conversion` | Canal y palabra clave vigentes | Falta el canal o la palabra clave |

## El orden importa en uno solo

`probatorio` corre **primero**, antes de resolver preset, paleta o aspecto.
Si el asset pedido es una prueba, no hay que generarlo, y todo lo que se
evalúe después se estaría evaluando sobre algo que no debería existir.

## Dato sin validar: escribe y avisa

El copy se escribe con la cifra que traiga la fuente —guión, brief, ficha—
y el dato queda marcado como pendiente en `pendientes.md`.

Lo que sí bloquea es la cifra que **no aparece en ninguna fuente**. Eso no
es republicar un dato viejo: es inventar una condición comercial, un plazo
o una especificación técnica del cliente.

## La negativa productiva

Un bloqueo siempre viene con el camino correcto. Para `probatorio` es un
plan de rodaje: qué registrar, qué planos, qué autorizaciones hacen falta,
y con qué se cubre el slot mientras tanto —un carrusel explicativo, una
FAQ, o saltear el slot antes que llenarlo con un asset que simule el hecho.

La razón es concreta: un error pelado deja a la agencia bloqueada y se
esquiva reformulando el pedido. El segundo intento es el que produce el
asset falso.
