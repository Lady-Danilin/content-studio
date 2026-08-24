---
description: Importa un plan de contenidos existente a un pack de content-studio
---

Importá el plan que indique el usuario. Si no dijo de dónde, preguntale por
la ruta —un JSON exportado, o un directorio con archivos TypeScript.

1. Llamá a `studio_importar` con `origen` y `nombre`.
2. Mostrá el resumen: cuántas marcas, cuántas piezas con id, cuáles quedaron
   sin calendario.
3. Corré `studio_huecos` y presentá lo que falta.
4. Dejá claro qué campos quedaron **vacíos a propósito** y por qué el core
   los va a pedir: permisos editoriales, canal de conversión, identidad
   visual, frases prohibidas.

Nunca completes un hueco con un valor plausible, ni siquiera "para probar".
Un pack con datos inventados es peor que un pack incompleto: el incompleto
avisa.

Si la fuente es un proyecto TypeScript y el extractor pierde campos, sugerí
`scripts/exportar-plan.mjs`, que usa el toolchain del propio proyecto.
