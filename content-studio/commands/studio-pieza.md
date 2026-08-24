---
description: Produce una pieza completa de una marca, del guión al paquete entregable
---

Producí una pieza. Pedile al usuario la marca y qué pieza si no lo dijo.

Orden, sin saltear pasos:

1. `studio_marca` — ficha, voz, permisos, frases prohibidas. **Antes de
   escribir una línea.**
2. `studio_piezas` — a qué id se adjunta. Si no hay calendario, va a staging
   sin id, y no se acuña ninguno.
3. Escribí el copy en la voz de esa marca. Si te apoyás en material de otra
   marca de la cartera, decilo en `origen_voz` al revisar.
4. `studio_gate` por cada asset que quieras generar, con `funcion` declarada
   (`prueba` o `ilustra`) y el `destino`.
5. Si el gate habilita: generá con `google-flow`, respetando sus reglas
   —dryrun antes de un lote, sin paralelizar, sin bajar las pausas.
6. `studio_revisar` sobre el copy final, pasando en `fuentes` los textos de
   donde salió cada dato duro.
7. `studio_paquete` para dejar copy, manifiesto y pendientes.

Al terminar, mostrale al usuario la ruta del paquete y **leele los
pendientes en voz alta**. Un paquete sin pendientes revisados se lee como
aprobado, y no lo está.
