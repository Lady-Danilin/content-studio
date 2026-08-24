# content-studio

El plugin. Once herramientas MCP, diez gates, un armador de paquetes.

## Herramientas

| Herramienta | Para qué |
|---|---|
| `studio_estado` | Qué pack está activo, qué cobertura tiene, si la sesión de Flow sirve |
| `studio_marca` | Ficha, voz, permisos, frases prohibidas y qué validar |
| `studio_piezas` | Piezas fechadas con su id permanente |
| `studio_huecos` | Qué falta para producir sin inventar nada |
| `studio_gate` | ¿Este asset se puede generar? Corre antes de gastar un crédito |
| `studio_revisar` | Un copy contra todos los gates de texto |
| `studio_formato` | Aspecto, medio y duración por destino |
| `studio_paquete` | Arma la carpeta entregable |
| `studio_importar` | Trae un plan externo a un pack |
| `studio_applet_spec` | Redacta el pedido de una applet de Flow |
| `studio_applet_descubrir` | Cablea los `appletId` en el pack |

Ninguna produce contenido. Habilitan, frenan y registran; la redacción y la
generación las hace el agente, o `google-flow`.

## Estructura

```
content-studio/
├── .claude-plugin/plugin.json
├── .mcp.json
├── doctor.py                    chequeo de instalación
├── lib/
│   ├── studio.py                config, packs, errores accionables
│   ├── plan.py                  marcas, grilla, piezas, huecos
│   ├── gates.py                 los diez gates
│   ├── formatos.py              contrato aspecto/duración por destino
│   ├── manifiesto.py            procedencia y no-atribución
│   ├── paquete.py               armado del entregable
│   ├── importar.py              plan externo → pack
│   ├── labs.py                  cliente de labs.google (stdlib)
│   └── applets.py               applets de Flow
├── mcp/server.py
├── hooks/                       precondiciones al arrancar
├── skills/content-studio/       cómo se opera, y por qué
├── commands/                    /studio-setup, /studio-importar, …
├── scripts/exportar-plan.mjs    exportador para planes en TypeScript
└── packs/_ejemplo/              pack ficticio, funcional
```

`lib/` viaja adentro del plugin a propósito: una vez instalado tiene que
funcionar sin depender de que otro repositorio esté presente.

## Probarlo sin instalar nada

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{}}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  | python3 content-studio/mcp/server.py

STUDIO_PACK_NAME=_ejemplo python3 content-studio/doctor.py
```

## Estado de la creación de applets

`studio_applet_spec` redacta la especificación completa y
`studio_applet_descubrir` cablea el `appletId` una vez que la applet existe.
El paso del medio —pegar la especificación en el agente de Flow— todavía es
manual, y se hace una vez.

Lo verificado contra la API, sin gastar créditos:

```
POST   flowCreationAgent/sessions   {"projectId": …}  → agentSessionId
GET    flowCreationAgent/sessions?projectId=…         → sesiones
GET    flowCreationAgent/sessions/{id}                → sessionInfo
DELETE flowCreationAgent/sessions/{id}                → {}
GET    flowAppletAgent/applets                        → catálogo
GET    flowAppletAgent/applets/{id}/versions/{v}      → código + conversación
```

Lo que falta es cómo se le manda el mensaje a la sesión. Se sondearon doce
rutas plausibles y todas responden 404, así que el envío viaja por otro
lado —probablemente el frontend—. Se descubre observando el tráfico real al
crear una applet, con DevTools, y se anota en `lib/applets.py`. Hasta
entonces `enviar_mensaje` falla con instrucciones en vez de adivinar un
endpoint de escritura sobre la cuenta de alguien.
