---
name: obsidian-make
description: Guide Obsidian plugin creation, updates, documentation, build, vault install, versioning, GitHub push, release publication, and archive cleanup for JaewonE plugin projects. Use when Codex is asked to create a new Obsidian plugin from the official sample plugin, modify an existing Obsidian plugin, update README/README.ko.md, bump plugin versions, build and install into a vault plugin folder, prepare or publish GitHub releases, or optimize an Obsidian plugin repo for handoff/archive.
---

# Obsidian Make

## Purpose

Use this skill as the shared policy guide for JaewonE Obsidian plugin work. It does not provide scripts or templates. Instead, it standardizes the repeated workflow: inspect nearby plugin conventions, keep Obsidian metadata synchronized, maintain bilingual documentation, build root release assets, install into the vault, and publish only when explicitly requested.

## Scope Discipline

Start every task by classifying the user's request:

- New plugin creation
- Existing plugin implementation or fix
- Documentation-only update
- Version bump and local vault install
- GitHub push/release publication
- Archive cleanup
- Patch/minor/full cycle
- Repo rename only

Keep the work inside the current Obsidian workspace unless the user gives another path. If the user narrows scope, such as "repo name only" or "do not publish", do not expand into README, manifest, code, tag, release, or submission work.

Treat Community Directory preparation, GitHub release publication, and final submission as separate actions. Do not submit to Obsidian Community Directory or `obsidianmd/obsidian-releases` unless the user explicitly asks for that action.

For Obsidian plugin work, interpret any request to push to GitHub, such as "GitHub에 push", "GitHub에 push까지", "push to GitHub", "publish to GitHub", "GitHub publication", or "GitHub에 올려라", as a full GitHub publication workflow: commit, push, create the matching Git tag, create the GitHub Release, upload release assets, and verify the uploaded manifest. Do not stop after branch push. Skip GitHub Release creation only when the user explicitly forbids it with language such as "release 생성 없이", "GitHub release 생성하지 마", "no release", "without a release", or "do not publish a release".

When the user explicitly asks for a "patch cycle" / "패치 사이클" or "minor cycle" / "마이너 사이클", treat that as a complete three-step Obsidian plugin workflow:

1. Implement the requested feature/fix and bump the version.
2. Publish to GitHub using the full GitHub publication policy.
3. Run archive cleanup after publication is complete.

If the user asks for a "cycle" / "사이클", "full cycle" / "전체 사이클", or equivalent without saying patch or minor and without giving an exact version, run a patch cycle by default. A patch cycle bumps the patch version by one step. A minor cycle bumps the minor version by one step. If the user gives an exact version, use that exact version while still running the full three-step cycle. Each step in the cycle must follow the matching policy in this skill: version synchronization, changelog and README policy, lint/build/vault install, GitHub commit/push/tag/release/asset verification, and archive cleanup.

## New Plugin Creation

When creating a new Obsidian plugin, start from the official sample plugin:

```bash
git clone https://github.com/obsidianmd/obsidian-sample-plugin.git <project-folder>
```

After cloning:

1. Rename the project folder to the requested project name.
2. Update `package.json`:
   - `name`: package/project slug.
   - `version`: initial requested version, otherwise `1.0.0`.
   - `description`: concise plugin description.
   - `author`: `JaewonE`.
   - `homepage` or `authorUrl` when applicable: `https://github.com/jaewonE`.
3. Update `manifest.json`:
   - `id`: Obsidian plugin id, usually lowercase/hyphen slug.
   - `name`: human-readable plugin name.
   - `version`: same as `package.json`.
   - `description`: same intent as package/repo description.
   - `author`: `JaewonE`.
   - `authorUrl`: `https://github.com/jaewonE`.
   - `isDesktopOnly`: match the actual API usage.
4. Update `versions.json` so the plugin version maps to `manifest.json.minAppVersion`.
5. Remove `.github/` or GitHub Actions workflows from the cloned sample if present, unless the user explicitly wants CI.
6. Check the actual sample structure before editing. The implementation entrypoint is usually `src/main.ts`, with settings in `src/settings.ts`.
7. Inspect sibling plugin repos before finalizing conventions for scripts, README wording, manifest fields, license, release assets, and vault install path.

Do not copy implementation patterns blindly. Use sibling repos as convention references, then adapt to the current plugin's requested behavior.

## Repository And Metadata Rules

Keep these identities distinct:

- GitHub repository name
- project folder name
- `package.json.name`
- `manifest.json.id`
- displayed plugin name in `manifest.json.name`

Do not change all of them just because one changes. If the user asks for a repository rename only, update the GitHub repo/local remote only and leave plugin metadata and docs untouched.

For Community Directory readiness:

- Avoid `obsidian` and `plugin` in `manifest.json.id` unless there is a strong repo-specific reason and policy permits it.
- Ensure release tags match `manifest.json.version` exactly.
- Ensure release assets include `main.js`, `manifest.json`, and `styles.css` when `styles.css` exists or is expected by the repo.
- Keep the repo public and include expected root files such as `README.md`, `LICENSE`, `manifest.json`, and `versions.json` when preparing for submission.

## Versioning Policy

For ordinary task completion, bump the patch version by one step:

- `0.0.1` -> `0.0.2`
- `1.2.3` -> `1.2.4`

Use the repo's existing version flow when available:

```bash
npm version <version> --no-git-tag-version
```

Prefer this when `package.json` has:

```json
"version": "node version-bump.mjs && git add manifest.json versions.json"
```

The version change must be reflected consistently in:

- `package.json`
- `package-lock.json`, if present
- `manifest.json`
- `versions.json`
- `README.md`
- `README.ko.md`
- `CHANGELOG.md`

If the user explicitly requests a GitHub push/release workflow:

- If the user gives a version, use that exact version.
- If the user does not give a version, bump the minor version instead of a patch version:
  - `0.2.3` -> `0.3.0`
  - `1.2.3` -> `1.3.0`
- Do not apply an extra patch bump on top of the release version.

Cycle requests override the default GitHub publication version rule. For a patch cycle, bump the patch version even though the cycle includes GitHub publication. For a minor cycle, bump the minor version. For an unspecified cycle with no exact version, use the patch-cycle default. If an exact version is supplied, use that version and do not apply an additional patch or minor bump.

Before changing versions, inspect current versions in `package.json`, `manifest.json`, and `versions.json`; do not assume they are aligned.

## CHANGELOG Policy

After each completed task, update `CHANGELOG.md`.

If the file does not exist, create it with a concise standard structure:

```markdown
# Changelog

## <version>

- <current behavior or fix summary>
```

Write entries as current release notes, not as noisy process history. Mention user-visible behavior, policy compliance, docs updates, build/release changes, and compatibility fixes. Avoid internal narration such as "Codex changed..." or "previously this was...".

## README Policy

Always maintain both:

- `README.md` in English.
- `README.ko.md` in Korean with equivalent content.

Both files must start with the same title and a language navigator immediately after the title. Use this exact shape, replacing the GitHub path:

```markdown
# Plugin Name

[ [English](https://github.com/jaewonE/<repo-name>) | [한국어](https://github.com/jaewonE/<repo-name>/blob/master/README.ko.md) ]
```

If the default branch is not `master`, use the actual default branch in the Korean README URL.

Recommended README sections:

- Short plugin description.
- Feature list.
- Usage instructions.
- Commands and Hotkeys, when the plugin registers commands.
- Settings, when the plugin has settings.
- Privacy and Network Access.
- Mobile/Desktop support and `isDesktopOnly` rationale.
- Installation from Community Plugins, if intended.
- Manual installation with `main.js`, `manifest.json`, and `styles.css`.
- Development commands.
- Community Plugin release notes, when release-oriented.
- License.

When docs are updated after implementation, describe the current behavior only. Do not write change-history wording such as "unlike before" unless the user explicitly asks for a migration note.

For commands and hotkeys:

- Do not assign default hotkeys unless the user explicitly asks and reviewer policy allows it.
- Document that users can assign shortcuts in Obsidian `Settings -> Hotkeys`.
- List command names that are assignable to hotkeys.

For privacy/network text:

- State whether the plugin uses network access.
- State whether it reads files outside the current vault.
- State where settings are stored when relevant.
- For destructive or vault-wide edits, include backup/rollback guidance.

## Build And Vault Install Policy

After each completed task, build the plugin and install the built release files into the Obsidian vault plugin folder.

Use the repository's existing build command unless it conflicts with the user's instruction:

```bash
npm install
npm run lint
npm run build
```

Run `npm install` when `node_modules/` is absent or dependencies are stale. Run `npm run lint` when the repo provides it. Run tests when the repo provides them and the change touches behavior or shared logic.

The canonical build outputs for this workspace are root-level release files:

- `main.js`
- `manifest.json`
- `styles.css`

Do not store release files under `build/` unless the user explicitly asks or the target repo's current contract requires it. If an older sibling repo uses `build/`, verify the current repo's release contract before reusing that pattern.

Install by copying root release files into:

```text
<Vault>/.obsidian/plugins/<plugin-id>/
```

Use `manifest.json.id` as `<plugin-id>` unless the user gives a different install folder. Create the folder if needed. Copy with overwrite semantics. If both old and new plugin-id folders exist, compare `manifest.json`, `main.js`, and `styles.css` before removing any stale duplicate, and only remove duplicates when the user wants a single install path.

## GitHub Push And Release Policy

By default, do not commit, push, tag, or publish releases after ordinary work. Stop after local changes, version bump, changelog update, build, and vault install unless the user explicitly asks to put the work on GitHub.

In this Obsidian plugin workflow, "put the work on GitHub" always includes release publication unless the user explicitly says to skip release creation. Do not treat `git push` as the finish line. A GitHub publication task is complete only after the commit is pushed, the matching tag is pushed, the release exists, required assets are uploaded, and the uploaded manifest has been inspected or downloaded and compared with the local release manifest.

When the user explicitly asks for GitHub publication:

1. Apply the release versioning rule:
   - explicit version: use it;
   - no explicit version: bump minor version.
2. Re-run build immediately before committing.
3. Commit intentional changes only.
4. Create a Git tag matching `manifest.json.version` exactly, without a leading `v` unless the repo already uses that convention.
5. Push the branch and tag.
6. Create a GitHub Release.
7. Upload release assets:
   - `main.js`
   - `manifest.json`
   - `styles.css`
8. Download or inspect the uploaded `manifest.json` and verify it matches the local release manifest.

If the code was already committed and pushed before this checklist was completed, continue from the current state instead of bumping the version again: create the missing tag if needed, push the tag, create or update the GitHub Release for the current `manifest.json.version`, upload the current root release assets, and verify the uploaded manifest.

If `gh` is unavailable, use the GitHub REST API with credentials from `git credential fill`. Do not stall just because `gh` is missing.

For GitHub About/repo metadata sync, align the repository description with `manifest.json.description` when the user asks for release polish or metadata sync.

## Reviewer And Community Policy

When the user refers to Obsidian reviewer policy, reviewer feedback, or Community Directory preparation:

- Treat the provided reviewer/submission document as the governing checklist.
- Remove default hotkeys unless explicitly approved.
- Avoid APIs that require a higher Obsidian version than `manifest.json.minAppVersion`.
- Keep `isDesktopOnly` honest. If the plugin uses Node/Electron APIs, set it accordingly.
- Keep release assets at the repo root when that is the current project policy.
- Validate the manifest, docs, version tag, and release assets before claiming readiness.

## Archive Cleanup Policy

Only run archive cleanup when the user asks to optimize, archive, or remove reproducible artifacts.

Before cleanup:

- Ensure required release publication is already complete if the user wanted a release.
- Check ignored/tracked state.
- Identify generated or reproducible files.

Safe cleanup candidates commonly include:

- `node_modules/`
- root `main.js`
- `build/`, when not the authoritative release source
- `.DS_Store`
- generated sourcemaps

Do not delete tracked source, docs, manifest files, `versions.json`, release metadata, or assets such as demos unless the user explicitly asks. Large tracked assets are not automatically disposable.

## Final Reporting

When finishing an Obsidian plugin task, report:

- Files changed at a high level.
- Final version.
- Build/lint/test commands run.
- Vault install path.
- Whether GitHub commit/push/release was intentionally skipped or completed.
- Release URL and asset verification when publication was performed.

Keep the report concise and grounded in actual commands/results.
