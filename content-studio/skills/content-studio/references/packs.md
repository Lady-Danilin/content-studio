# Packs

El core sirve a cualquier agencia de contenidos. Un pack es la parte que no
puede ser genérica.

| | Por qué no puede viajar en el plugin |
|---|---|
| Marcas, slugs, rubros | Son los clientes de una agencia concreta |
| Voz, muletillas, frases ancla | La voz es intransferible y es parte del producto |
| Presets de generación | Dirección visual de una marca concreta |
| Frases prohibidas | Historia comercial de ese cliente |
| Palabras clave de conversión | Mecanismo de medición de cada cuenta |
| Pares de vecindad peligrosa | Depende de qué clientes conviven en la cartera |
| Grillas y cadencia | Es el plan de medios contratado |
| Carácter de audio | Dirección sonora, con sus prohibiciones cruzadas |

**La regla: si otra agencia no lo puede usar tal cual, es pack.**

El core tiene que funcionar sin ningún pack. Un pack agrega atajos, no
capacidades: si una herramienta sólo anda con pack, está mal diseñada.

## Dónde vive

En `~/.config/content-studio/packs/<nombre>/`, **fuera de git**. No es una
preferencia: un pack contiene direcciones, teléfonos, aranceles, nombres de
profesionales con matrícula, condiciones comerciales y qué puede y no puede
decir cada cuenta. Publicarlo expone a los clientes, no a la agencia.

Se elige con `STUDIO_PACK_NAME`, o con `STUDIO_PACK` apuntando a cualquier
ruta. Con un solo pack instalado se usa ése.

## Cómo se llena

```
studio_importar   origen: <ruta al plan>   nombre: <agencia>
```

Importar **no completa nada**. Lo que la fuente no trae queda declarado
como hueco con su nombre, y `studio_huecos` los lista. Los campos que el
core necesita y una fuente típica no tiene:

- `permisos` — `trend`, `humor`, `crudo` por marca, con valores
  `permitido` / `prohibido`. Lo que no está declarado **bloquea y
  pregunta**; no se hereda del cluster.
- `conversion` — `canal`, `palabra_clave`, `verificado`. Sin esto todo CTA
  cae al vacío y la métrica no mide nada.
- `identidad_visual` — `disponible`, `faltan`. Sin esto las piezas salen
  marcadas `incompleta`, que es lo correcto.
- `prohibido` — las frases vedadas. Ojo: suelen estar escritas en la propia
  ficha de la marca *como prohibición*, y un generador que lee esa ficha
  las ve como copy disponible.
- `sector_regulado` — se infiere del rubro, pero conviene revisarlo: un
  falso negativo es una promesa clínica publicada.
- `pares_peligrosos` — la lista sugerida sale de cluster y rubro. Revisala:
  quien conoce la cartera sabe cuáles se confunden de verdad.

## Presets

Un preset es una receta de generación con la estética de una marca:

```json
{
  "presets": {
    "fondo-placa": {
      "titulo": "Fondo de placa",
      "para_que": "Fondos y texturas para placas, sin texto",
      "prompt": "superficie de papel prensado, luz lateral suave, …",
      "aspecto": "1:1",
      "medio": "imagen",
      "boton": "GENERAR FONDO",
      "marcas": ["marca-a", "marca-b"],
      "controles": [
        {"etiqueta": "Textura", "tipo": "desplegable",
         "valores": ["Papel", "Cemento", "Tela"], "para_que": "superficie base"}
      ]
    }
  }
}
```

`studio_applet_spec fondo-placa` lo convierte en el pedido para el agente
de Flow, con el selector de modelo ya incluido.
