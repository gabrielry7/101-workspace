# 101 Workspace

Private consolidated workspace for UnoCeroUno / 101. Source originals were preserved. Large QA evidence and original archives are stored in the GitHub Release and restored using verified checksums.

## Included projects

- `projects/101-design-compiler`: current Astro/TypeScript compiler source, fixtures, production assets, scripts, contracts, documentation and previously untracked review material.
- `projects/101_restaurant_commerce_v4`: standalone Python restaurant subsystem. Integration into the world model remains a separate task.
- `projects/google_maps_identity_toolkit_v2`: identity-review toolkit.
- `projects/google_maps_status_probe`: prior Maps probe version, preserved separately.
- `projects/pipeline-101-v2.1.1`: original pipeline package.
- `documents/Desktop`, `documents/Downloads`, `documents/archived-handoffs`: specifications, plans, older versions and handoffs.

`admin/inventory.csv` records original absolute paths, sizes and SHA-256 checksums. `admin/project-summary.json` records project totals; `admin/duplicates.json` identifies identical files without discarding their original provenance. `asset-manifest.json` records every Release-backed file, restored relative path, archive volume, size and SHA-256 checksum.

`admin/supplement-inventory.csv` additionally records required original media and archived experiment sources recovered from `.tools`. These are restored through the Release rather than omitted with the disposable caches. Small production images/videos required by the application are committed in Git; browser profiles, cookies and credentials are excluded.

The `/home/t/101-world-model` checkout mentioned in handoffs was not found on this Windows computer. These handoffs and standalone bundles do not substitute for the complete repository on that other computer.

Excluded: secrets and `.env` files, installed dependencies, downloaded runtime tools, local assistant caches/configuration, rebuildable outputs and unrelated personal, music, university and employer material. No Git LFS or paid storage feature was enabled. Large evidence is archival and does not need file-level LFS versioning.

## Clone and restore

Install Git, GitHub CLI and 7-Zip. Authenticate with your own GitHub account:

```powershell
gh auth login --hostname github.com --git-protocol https --web
gh auth setup-git
gh repo clone gabrielry7/101-workspace
cd 101-workspace
powershell -NoProfile -ExecutionPolicy Bypass -File ./restore-assets.ps1 -Repository gabrielry7/101-workspace
```

The restoration script downloads the Release volumes, verifies each SHA-256 checksum, extracts the lossless split 7z archive and verifies every restored file. Assets return to project-relative paths. Original ZIP packages are restored under `archives/originals`. Keep downloaded volumes until verification succeeds. If an interrupted download leaves a corrupt volume, move that volume aside and rerun the script. The script intentionally refuses corrupt downloads rather than silently replacing them.

Run restoration on a fresh clone before editing files at the restored paths: archive extraction overwrites files at those paths. Those restored paths are ignored by Git.

The original compiler history, including all local branches, is preserved in `archives/history/101-design-compiler.bundle`. To inspect it separately:

```powershell
git clone archives/history/101-design-compiler.bundle 101-design-compiler-history
git -C 101-design-compiler-history branch --all
```

The published monorepo starts with a source snapshot so bulky historical QA artifacts do not enter ordinary Git history. The original repository and its history remain unchanged locally. The archived history was scanned for credential patterns before publication.

## Run the compiler

Install Node 24 LTS, restore assets, then:

```powershell
cd projects/101-design-compiler
npm ci
New-Item -ItemType Directory -Force .tools
npm run validate
npm test
npm run check
npm run build
npm run dev
```

Restore assets before running tests or builds: the B2 media admission gate requires byte-identical originals restored inside `.tools/b2-demo/originals`. `.tools` also contains disposable test directories. The H8 lock verification test additionally requires the historical, exact Edge binary/version, Windows build, fonts, Node executable and dependency bytes recorded in `fixtures/locks/h8/pilot-flow.json`. A different host or an automatically updated Edge can produce `LOCK_BROWSER_MISMATCH`; that is a locked-environment limitation, not a missing source file. See `admin/local-validation.json` for actual results; do not assume every historical lock test passes on a new machine.

See each Python project's README for installation and execution. Use one virtual environment per project and install its `requirements.txt` or `pyproject.toml` dependencies. Browser tools also require Playwright Chromium. No live business probes, payments or provider integrations were run during publication.

## Collaborating

Inspect invitations:

```powershell
gh api repos/gabrielry7/101-workspace/invitations
gh api repos/gabrielry7/101-workspace/collaborators/thomaspradae/permission
```

Thomas signs into his own account and accepts the matching invitation:

```powershell
gh auth login --hostname github.com --git-protocol https --web
gh api user/repository_invitations
gh api --method PATCH user/repository_invitations/INVITATION_ID
gh repo clone gabrielry7/101-workspace
```

Personal repositories have one owner. Collaborator write access allows clone, pull and push; commits are created locally. Write permission does not grant full administration or ownership. To share administrative control, create a GitHub organization, then transfer the repository through the official API:

```powershell
gh api --method POST repos/gabrielry7/101-workspace/transfer -f new_owner=ORG
# Wait for transfer completion, then inspect the new repository.
gh api repos/ORG/101-workspace
gh api --method PUT repos/ORG/101-workspace/collaborators/thomaspradae -f permission=admin
gh api repos/ORG/101-workspace/collaborators/thomaspradae/permission
```

Grant the operator an appropriate organization/repository role too. Organization creation, billing and transfer were not performed automatically.

Continue development in this workspace or a clone. Use small commits and normal pushes; never force-push or commit secrets. Example:

```powershell
git status --short
git add PATHS_YOU_REVIEWED
git diff --cached --stat
git commit -m "Describe the change"
git push
```

