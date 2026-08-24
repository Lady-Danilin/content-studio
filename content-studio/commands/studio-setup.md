---
description: Verifica la instalación de content-studio y guía la puesta a punto del pack
---

Poné a punto `content-studio` de punta a punta.

1. Corré `python3 ${CLAUDE_PLUGIN_ROOT}/doctor.py` y mostrá el resultado.
2. Llamá a `studio_estado` para ver qué pack está activo.
3. Si no hay ninguno, explicá las dos opciones y ofrecelas:
   - importar un plan existente con `/studio-importar`
   - empezar de cero copiando `packs/_ejemplo`
4. Si hay pack, corré `studio_huecos` y presentá lo que falta **agrupado por
   tipo de faltante**, no marca por marca: es más accionable pedir todos los
   canales de conversión juntos que ir cliente por cliente.
5. Si las cookies de labs.google no están en modo 600, decilo: es una sesión
   completa de Google.

No produzcas contenido en este comando. Es puesta a punto.
