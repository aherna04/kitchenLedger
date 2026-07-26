# Changelog

## 2026.07.25

### Added

- Initial Kitchen Ledger app: scan inbox images, OCR-assisted draft recipes, ingredients/directions editing, multi-tag AND filtering, and Docker Compose setup.
- Optional per-recipe **hero** dish photo (stem match from `hero/` and manual **Link as hero to…** from Inbox).
- Inbox as a **review queue**: Scan indexes only; **Mark reviewed** moves scans to `recipes/`; linking as hero moves the dish photo to `hero/` and removes the orphan draft.

### Fixed

- Move reviewed scans still sitting in `inbox/` into `recipes/` on save (self-heal for recipes already marked reviewed).
- Cache-bust hero and scan image URLs with file mtime so replaced dish photos show immediately.
