---
description: Muestra qué le falta a la cartera para poder producir sin inventar nada
---

Corré `studio_huecos` y presentá el resultado de forma accionable.

Agrupá **por tipo de faltante**, no por marca: es más útil pedirle al
usuario todos los canales de conversión de una vez que ir cliente por
cliente.

Para cada grupo decí qué se rompe si falta:

- sin calendario → los assets van a staging sin id
- sin identidad visual → las piezas salen marcadas `incompleta`
- sin canal de conversión → los CTA caen al vacío
- sin permisos declarados → se bloquea y se pregunta, no se hereda del cluster
- sin inventario → no se sabe si un slot probatorio se cubre o hay que filmar

Cerrá con lo que conviene resolver primero, y por qué. No inventes ningún
valor para tapar un hueco.
