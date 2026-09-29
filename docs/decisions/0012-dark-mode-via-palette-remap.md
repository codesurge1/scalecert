# 0012 — Dark mode: semantic token block plus a palette-variable remap for the printed-form tables

## Status

Accepted

## Context

The app's semantic design tokens (`--background`, `--primary`, `--muted`, …) were built so that dark mode would only need a second `.dark` block. The printed OIML form tables, though, deliberately bypass those tokens to look like the black-on-white paper form: `bg-white`, `border-neutral-900`, `ring-neutral-900`, `text-neutral-600`, `bg-red-50`, `text-emerald-700`, `bg-amber-50`, and so on. That's about 500 raw palette classes across about 20 files (`WeighingFormTable`, `SessionSummaryTable`, `DisturbanceFormTable`, the eccentricity/discrimination/… tables, `FormPrimitives`). A token-only dark block would leave those tables as bright white sheets inside a dark app.

There was a second, smaller conflict. `--primary` doubled as the sidebar/top-bar background and as the link/button colour. Dark mode needs a *light* primary so `text-primary` links stay readable on dark surfaces, but a light-blue sidebar would be a glaring slab.

Options considered for the form tables:
1. Rewrite every raw class to new semantic "form" tokens (`bg-form-sheet`, `border-form-ink`, …): about 500 edits across about 20 files, easy to get subtly wrong, and every in-flight branch touching a form table would conflict.
2. Add `dark:` variants beside every raw class: the same edit volume, and it doubles the class noise in the densest files in the codebase.
3. Remap the palette variables themselves under `.dark`. Tailwind v4 compiles `bg-white` to `background-color: var(--color-white)` and `border-neutral-900` to `var(--color-neutral-900)`, so redefining those CSS variables inside `.dark` flips every use at once.

## Decision

Option 3, scoped narrowly. The `.dark` block in `src/index.css` redefines the semantic tokens and remaps only the palette variables the form tables actually use:
- The neutral scale is inverted: 900 "ink" becomes light and 50/100 "paper tint" becomes dark.
- `white` becomes the dark sheet colour.
- `red-50`/`amber-50`/`amber-200` become dark tints.
- `emerald-600/700`, `red-700` and `amber-500` become lighter shades that keep their pass/fail/active meaning.

`black` is not remapped, because it's only used for modal backdrops, which must stay dark. `slate` is not remapped, because VerifyPage already pairs it with explicit `dark:` variants and remapping would invert those.

For the sidebar conflict, new `--sidebar`/`--sidebar-foreground` tokens hold the app chrome colour. They're identical to primary in light mode, so light mode is pixel-for-pixel unchanged. `AppShell`/`FocusedShell` use them in place of `bg-primary`/`text-primary-foreground`.

The theme preference (Light, Dark or System) is applied as a `.dark` class on `<html>`. Tailwind's `dark:` variant is redefined to follow that class, so an explicit choice overrides the OS setting.

## Consequences

- Light mode's rendered output is unchanged. Every light-mode value is the same as before.
- Within dark mode, `bg-white` no longer means white. That's surprising if you don't know about it, so it's documented at the remap itself in `src/index.css` and in docs/architecture.md. New non-form code should use semantic tokens. A form table that introduces a new raw palette class (say `bg-sky-50`) needs a matching remap line, or it will render in its light colour in dark mode.
- If raw palette classes ever spread beyond the printed forms, revisit this in favour of option 1 in a new ADR that supersedes this one.
