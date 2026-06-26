# Repository Agent Policy

This repository stores reusable Codex skills. When adding or updating a skill folder, keep public and private documentation synchronized with the user's publication intent.

## Public Skills

If the user says a skill may be public, or gives no private restriction:

1. Keep the skill folder out of `.gitignore`.
2. Add or update a `## <skill-folder-name>` section in `README.md`.
3. Add or update the matching `## <skill-folder-name>` section in `README.ko.md`.
4. Each public skill section must include:
   - Skill Introduction
   - Usage
   - Cautions
5. Keep descriptions concise and avoid exposing local-only secrets, credentials, private repository names, private vault paths, or unpublished business details.

## Private Skills

If the user says a skill should stay private:

1. Add the skill folder name to `.gitignore`.
2. Do not document that skill in public `README.md` or `README.ko.md`.
3. Document it only in `PRIVATE_README.md` and `PRIVATE_README.ko.md`.
4. The private README files should use the same section shape as the public README files:
   - Skill Introduction
   - Usage
   - Cautions
5. Verify with `git status --ignored --short` that private skill folders and private README files are ignored before committing.

## Documentation Rules

- Keep `README.md` in English.
- Keep `README.ko.md` in Korean with equivalent public content.
- Keep `PRIVATE_README.md` and `PRIVATE_README.ko.md` local-only and ignored.
- When moving a skill between public and private status, update `.gitignore` and move the documentation between public and private README files in the same change.
- Before pushing, inspect `git status --short` and ensure only intended public files are staged.
