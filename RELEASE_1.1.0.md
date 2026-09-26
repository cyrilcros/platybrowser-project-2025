# Cutting release 1.1.0

`1.1.0` is a metadata-only release: it keeps the `1.0.1` data identically but
points every `bdv.n5.s3` source at the new NetApp bucket
(`https://buckets.embl.de`, bucket `platybrowser-n5-generic`).

## Steps

1. Copy the rewired `1.0.1` dataset to `1.1.0`:
   ```bash
   cp -r data/1.0.1 data/1.1.0
   # or: rsync -a data/1.0.1/ data/1.1.0/
   ```
2. Add `"1.1.0"` to the `datasets` array in `data/project.json`.
3. Optionally set `"defaultDataset": "1.1.0"`.
4. Commit and push.

No N5 data is copied; only XML metadata changes.

## Notes

- The bucket layout is 1:1 with the old Minio buckets, using the old bucket name
  as a key prefix:
  - old bucket `platybrowser` → key `platybrowser/…`
  - old bucket `platybrowser-2025` → key `platybrowser-2025/…`
  - old bucket `platybrowser-all-hcrs-temp` → key `platybrowser-all-hcrs-temp/…`
- Historical: `misc/outdated/update_minor.py` was the old automated release helper
  (depends on `mmpb`). For this metadata-only re-point the manual copy above is
  authoritative.
