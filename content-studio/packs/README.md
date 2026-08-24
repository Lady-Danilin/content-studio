# Packs

El plugin es genérico: sus herramientas sirven a cualquier agencia de
contenidos. Un pack es la parte que no puede serlo.

## Qué es específico de cada agencia

| | Por qué no puede viajar en el plugin |
|---|---|
| Marcas, slugs, rubros | Son los clientes de una agencia concreta |
| Voz y muletillas | La voz es intransferible: es parte del producto |
| Presets de generación | Dirección visual de una marca |
| Frases prohibidas | Historia comercial de ese cliente |
| Palabras clave de conversión | Cómo mide cada cuenta |
| Pares de vecindad peligrosa | Depende de qué clientes conviven |

Todo lo demás —los gates, el contrato de formato, el manifiesto, el armado
del paquete— es igual para todos y vive en el plugin.

## Generar el tuyo

```
studio_importar   origen: <ruta al plan>   nombre: <agencia>
```

Va por defecto a `~/.config/content-studio/packs/<nombre>/`, **fuera de
git**. No es una preferencia de estilo: un pack contiene direcciones,
teléfonos, aranceles, nombres de profesionales con matrícula, condiciones
comerciales y qué puede y no puede decir cada cuenta. Publicarlo expone a
los clientes, no a la agencia.

Es la misma política con la que `google-flow` mantiene sus `appletId` fuera
del repo, y acá la razón pesa más.

## Activarlo

```bash
export STUDIO_PACK_NAME=mi-agencia          # uno de los instalados
export STUDIO_PACK=/ruta/a/un/pack          # o una ruta cualquiera
```

Con un solo pack instalado se usa ése sin configurar nada.

## Escribirlo a mano

`pack.json` es un archivo común; el importador es una comodidad, no un
requisito. `_ejemplo/` es un pack **funcional** con dos marcas inventadas,
elegidas para que se disparen los gates que importan: una regulada, una sin
identidad visual, una sin calendario.

```bash
STUDIO_PACK_NAME=_ejemplo python3 content-studio/doctor.py
```

## Packs incluidos

Sólo [`_ejemplo`](./_ejemplo), con marcas ficticias.

**Este repositorio es público y no incluye ningún pack real**, a propósito.
