# Vendored: dsh-infinite-gen-5 prompts

Source: https://github.com/SunsetRNE/dsh-infinite-gen-5
License: MIT (see LICENSE in this folder), Copyright (c) 2026 SunsetRNE

Only the three prompt payloads used by wb-armor are vendored here so the bridge
does not depend on an external checkout path:

- `infinite-gen-5.1-flash.md`  (default, ~16 KB)
- `infinite-gen-5.full.md`     (fuller, ~24 KB)
- `infinite-gen-5-lazy.md`     (lazy-pointer variant, ~17 KB)

The bridge auto-falls back to these when `IG5_PAYLOAD` / `.payload` points at a
missing file. See CREDITS.md at repo root.
