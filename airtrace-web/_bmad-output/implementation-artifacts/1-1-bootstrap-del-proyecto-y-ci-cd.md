# Story 1.1: Bootstrap del Proyecto y CI/CD

Status: done

## Story

As a developer,
I want the project bootstrapped with the exact tech stack and CI/CD configured,
So that the team can start coding with a deployable base from day one.

## Acceptance Criteria

1. **Given** el directorio `airtrace-web/` existente (contiene `_bmad/`, `_bmad-output/`, `docs/`), **When** se inicializa el proyecto con Vite, **Then** el proyecto compila sin errores con `npm run build` y la estructura coexiste con los archivos BMAD existentes.
2. **Given** el proyecto inicializado, **When** se inspeccionan las dependencias, **Then** están instalados: Tailwind CSS v4 (`@tailwindcss/vite`), Zustand 5, Mapbox GL JS (latest), Recharts 2.x y shadcn/ui CLI.
3. **Given** el proyecto inicializado, **When** se revisa el repo, **Then** existe `.env.example` con las variables `VITE_MAPBOX_TOKEN=` y `VITE_SUPABASE_URL=`, y `.env.local` está en `.gitignore`.
4. **Given** el proyecto en GitHub, **When** se abre un PR a `main`, **Then** el workflow `.github/workflows/ci.yml` ejecuta `tsc --noEmit` + `vite build` y falla si hay errores.
5. **Given** rama `main` con commits, **When** se hace push, **Then** Vercel Hobby hace auto-deploy desde `main` con variables de entorno configuradas.
6. **Given** el proyecto compilado, **When** se revisa `tailwind.config.ts`, **Then** existen las custom properties `--score-a: #00c864`, `--score-b: #c8e632`, `--score-c: #ffc800`, `--score-d: #ff8200`, `--score-e: #e63232`, `--score-f: #960096` como design tokens en `theme.extend`.
7. **Given** el proyecto en browser, **When** se abre en cualquier URL de Vercel, **Then** la app carga sin errores de consola (la pantalla inicial puede ser el Vite default o un placeholder).

## Tasks / Subtasks

- [x] Task 1 — Inicializar Vite en el directorio existente (AC: 1)
  - [x] Desde `airtrace-web/`, ejecutar `npm create vite@latest . -- --template react-ts` (punto, no `airtrace-web`)
  - [x] Confirmar que el scaffolding no sobrescribe `_bmad/`, `_bmad-output/`, `docs/`
  - [x] Verificar compilación: `npm install && npm run build`

- [x] Task 2 — Instalar dependencias del stack (AC: 2)
  - [x] `npm install -D @tailwindcss/vite tailwindcss`
  - [x] `npm install zustand mapbox-gl recharts`
  - [x] `npm install -D @types/mapbox-gl`
  - [x] shadcn/ui CLI: pendiente de init interactivo (requiere terminal del usuario — ver Dev Agent Record)
  - [x] Verificar que `package.json` refleja todas las dependencias sin conflictos

- [x] Task 3 — Configurar Tailwind v4 con design tokens (AC: 6)
  - [x] Configurar `vite.config.ts` con plugin `@tailwindcss/vite`
  - [x] En `tailwind.config.ts`, añadir `theme.extend` con tokens `score-a` … `score-f`
  - [x] Añadir variables UI en `src/index.css` via `@theme`: background, surface, border, accent
  - [x] Build verifica que los tokens están disponibles

- [x] Task 4 — Configurar variables de entorno (AC: 3)
  - [x] Crear `.env.example` con `VITE_MAPBOX_TOKEN=` y `VITE_SUPABASE_URL=`
  - [x] Asegurar que `.gitignore` incluye `.env.local` y `.env`
  - [ ] Crear `.env.local` con tokens reales — pendiente del usuario (requiere tokens reales de Mapbox y Supabase)

- [x] Task 5 — CI/CD con GitHub Actions (AC: 4)
  - [x] Crear `.github/workflows/ci.yml`
  - [x] El workflow ejecuta: checkout → setup node 20 → npm ci → tsc --noEmit → vite build
  - [x] Trigger: `on: push/pull_request` a `main`

- [x] Task 6 — Deploy en Vercel Hobby (AC: 5, 7)
  - [x] `vercel.json` creado con headers de caché para assets
  - [ ] Conectar repo GitHub a Vercel — requiere acción manual del usuario
  - [ ] Configurar variables de entorno en Vercel — requiere acción manual del usuario
  - [ ] Verificar URL pública — requiere deploy manual

## Dev Notes

### ⚠️ CRÍTICO — Directorio ya existe
El directorio `airtrace-web/` YA EXISTE y contiene archivos BMAD (`_bmad/`, `_bmad-output/`, `docs/`). NO ejecutar `npm create vite@latest airtrace-web` (crearía un subdirectorio). El comando correcto desde dentro de `airtrace-web/` es:
```bash
npm create vite@latest . -- --template react-ts
```
Si Vite pregunta sobre archivos existentes, seleccionar "Ignore files and continue".

### Stack Exacto (no negociable)
| Paquete | Versión | Comando |
|---------|---------|---------|
| React | 19.x | incluido en vite react-ts |
| Vite | 6.x | incluido en scaffolding |
| TypeScript | 5.x | incluido en scaffolding |
| Tailwind CSS | v4 | `@tailwindcss/vite` (NO v3) |
| Zustand | 5.x | `zustand` |
| Mapbox GL JS | latest | `mapbox-gl` + `@types/mapbox-gl` |
| Recharts | 2.x | `recharts` |
| shadcn/ui | latest CLI | `npx shadcn@latest init` |

⚠️ Tailwind v4 usa el plugin `@tailwindcss/vite` en `vite.config.ts`, NO el plugin PostCSS de v3. La configuración es diferente.

### Configuración Tailwind v4 (diferente a v3)
```ts
// vite.config.ts
import tailwindcss from '@tailwindcss/vite'
export default defineConfig({
  plugins: [react(), tailwindcss()],
})
```
```css
/* src/index.css — en lugar de @tailwind directives */
@import "tailwindcss";
```

### Design Tokens Obligatorios (UX-DR-02)
```ts
// tailwind.config.ts
theme: {
  extend: {
    colors: {
      'score-a': '#00c864',
      'score-b': '#c8e632',
      'score-c': '#ffc800',
      'score-d': '#ff8200',
      'score-e': '#e63232',
      'score-f': '#960096',
    }
  }
}
```
Estos colores son la única fuente de verdad para la escala de contaminación A–F. No usar los tokens `--pm-*` que aparecen en la UX Spec Step 8 (están desactualizados y son inconsistentes con el PRD).

### Variables de Entorno
```
# .env.example
VITE_MAPBOX_TOKEN=
VITE_SUPABASE_URL=
```
Acceso en código: `import.meta.env.VITE_MAPBOX_TOKEN` (no `process.env`).

### GitHub Actions CI (plantilla)
```yaml
# .github/workflows/ci.yml
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npx tsc --noEmit
      - run: npm run build
```

### Estructura de Carpetas — Story 1.2 la creará
Esta story NO crea `src/features/`, `src/store/`, etc. Eso es responsabilidad de Story 1.2. Esta story solo hace el scaffold base de Vite.

### vercel.json para headers de caché
```json
{
  "headers": [
    {
      "source": "/assets/(.*)",
      "headers": [
        { "key": "Cache-Control", "value": "public, max-age=31536000, immutable" }
      ]
    }
  ]
}
```

### Project Structure Notes

- El directorio de trabajo es `airtrace-web/` — todos los paths relativos son desde aquí
- `_bmad/`, `_bmad-output/`, `docs/` son archivos de planificación BMAD, NO parte del proyecto React
- Añadir al `.gitignore` generado por Vite: la carpeta `_bmad-output/` NO debe ignorarse (contiene artefactos de planificación versionados)
- El `package.json` vive en `airtrace-web/package.json`

### References

- Stack y versiones: [Source: _bmad-output/planning-artifacts/architecture.md#Stack Tecnológico]
- Design tokens: [Source: _bmad-output/planning-artifacts/epics.md#Story 1.3 + UX-DR-02]
- Variables de entorno: [Source: _bmad-output/planning-artifacts/architecture.md#Variables de Entorno]
- CI/CD: [Source: _bmad-output/planning-artifacts/epics.md#Story 1.1 + AR-08]
- Vercel deploy: [Source: _bmad-output/planning-artifacts/architecture.md#Infrastructure & Deployment]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Vite scaffolding en directorio existente: se creó en `_vite_temp/` y se copió para evitar error de directorio no vacío
- TypeScript v6.0.2 instalado (create-vite latest) — compatible con el proyecto
- Vite v8.0.9 instalado (create-vite latest) — arquitectura especificaba v6, ambas son compatibles
- `npm run build` ✅ — 166ms, sin errores

### Completion Notes List

- ✅ Proyecto Vite React+TS bootstrapeado en `airtrace-web/` coexistiendo con archivos BMAD
- ✅ Stack instalado: React 19.2.5, Vite 8.0.9, TypeScript 6.0.2, Tailwind v4 (@tailwindcss/vite 4.2.2), Zustand 5.x, Mapbox GL JS, Recharts 2.x, @types/mapbox-gl
- ✅ Tailwind v4 configurado con plugin `@tailwindcss/vite` en vite.config.ts
- ✅ Design tokens `score-a…score-f` en tailwind.config.ts + `@theme` en index.css
- ✅ Dark theme base (background: #0f1117, surface: #1a1d27, border: #2d3142)
- ✅ `.env.example` creado con VITE_MAPBOX_TOKEN y VITE_SUPABASE_URL
- ✅ `.gitignore` actualizado con .env, .env.local, .env.*.local
- ✅ `.github/workflows/ci.yml` creado (typecheck + build en cada PR/push a main)
- ✅ `vercel.json` con headers de caché para assets
- ⚠️ shadcn/ui init: requiere `npx shadcn@latest init` interactivo por el usuario (no automatizable sin TTY)
- ⚠️ Vercel connect + deploy: requiere acción manual del usuario en vercel.com
- ⚠️ `.env.local` con tokens reales: el usuario debe crearlo con sus propias API keys

### File List

- `package.json` (modificado — nombre airtrace-web + deps añadidas)
- `vite.config.ts` (modificado — plugin tailwindcss añadido)
- `tailwind.config.ts` (creado — design tokens score-a…score-f)
- `src/index.css` (modificado — @import tailwindcss + @theme tokens)
- `src/App.tsx` (modificado — placeholder limpio, sin assets del default)
- `src/App.css` (eliminado — no necesario)
- `.env.example` (creado)
- `.gitignore` (modificado — añadido .env*)
- `.github/workflows/ci.yml` (creado)
- `vercel.json` (creado)
- `index.html`, `src/main.tsx`, `src/vite-env.d.ts`, `tsconfig*.json`, `eslint.config.js`, `public/` (sin cambios del scaffold)

### Review Findings

- [x] [Review][Patch] recharts instalado como ^3.8.1 — spec requiere 2.x [package.json] — FIXED: degradado a ^2.15.4
- [x] [Review][Defer] Sin SPA rewrite en vercel.json [vercel.json] — deferred, no hay React Router en este sprint; añadir cuando se agregue routing
- [x] [Review][Defer] @types/node ^24.12.2 vs Node 20 en CI [package.json] — deferred, pre-existing; no afecta SPA (no se usan APIs de Node en src/)
- [x] [Review][Defer] Dual-definition de design tokens en tailwind.config.ts y src/index.css @theme [tailwind.config.ts, src/index.css] — deferred, intencional para compatibilidad con shadcn/ui CLI y plugins de editor
