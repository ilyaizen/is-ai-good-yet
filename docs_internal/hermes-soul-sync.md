# Hermes soul sync

## What is live

- `~/.hermes/SOUL.md` is the live persona source of truth used by Hermes at runtime.
- The vault copy under `HyperVault/Projects/is-ai-good-yet/` is a human-readable mirror.

## What not to do

- Do not make the vault note a symlink to `~/.hermes/SOUL.md`.
- Do not rely on the rclone/Google Drive layer to preserve symlink semantics.
- Do not edit only the vault copy and assume Hermes will pick it up.

## Safe workflow

1. Edit `~/.hermes/SOUL.md`.
2. Mirror the same content into the vault note as plain markdown.
3. Restart the Hermes gateway or start a fresh session if you need the new persona to apply immediately.

## Why this matters

Symlinks are filesystem metadata. rclone/Drive sync is about files, not live link resolution. If you treat the vault note as the source of truth, the mirrored copy and the runtime persona drift apart.
