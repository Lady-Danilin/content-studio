#!/usr/bin/env node
/**
 * Exporta un plan de contenidos que vive en TypeScript a JSON.
 *
 * Se corre DENTRO del proyecto que tiene el plan, con su propio toolchain:
 * ese proyecto sabe compilar su TypeScript, y este script no tiene que
 * adivinar cómo.
 *
 *   node scripts/exportar-plan.mjs ./content/marcas/index.ts plan.json
 *
 * Después:
 *   studio_importar  origen: plan.json  nombre: <agencia>
 *
 * Es preferible al extractor de literales que trae el plugin: éste ve los
 * imports, los spreads y los valores calculados; aquél no.
 */
import { writeFileSync } from "node:fs";
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";

const [, , entrada, salida = "plan.json"] = process.argv;

if (!entrada) {
  console.error("uso: node exportar-plan.mjs <modulo-del-plan> [salida.json]");
  process.exit(1);
}

const mod = await import(pathToFileURL(resolve(entrada)).href);

// Aceptamos las formas habituales: un objeto por slug, un array, o un
// export con nombre. Lo que no encaje se informa en vez de adivinarse.
const candidato =
  mod.MARCAS ?? mod.marcas ?? mod.default ?? mod.BRANDS ?? null;

if (!candidato) {
  console.error(
    `No encontré el plan en ${entrada}. Exports disponibles: ${Object.keys(mod).join(", ")}.\n` +
      "Exportá las marcas como MARCAS, marcas o default."
  );
  process.exit(1);
}

const marcas = Array.isArray(candidato)
  ? Object.fromEntries(candidato.map((m) => [m.slug ?? m.id, m]))
  : candidato;

writeFileSync(salida, JSON.stringify({ marcas }, null, 2) + "\n", "utf8");
console.log(`${Object.keys(marcas).length} marcas → ${salida}`);
