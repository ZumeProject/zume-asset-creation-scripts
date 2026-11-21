# Review master lists

On-demand caches written by:

```bash
python3 -m zume_assets review fetch-master --lang en --type 10
```

Files are named `{lang}-{type}.json` (for example `en-10.json`, `es-10.json`).
CI stays offline by default; refresh when you need live API metadata for a locale.

These JSON files may be committed so offline `review qr` / `review videos` can re-run without the network.
