# Security & Trust Model

Semantic File Aggregator is a local-only file utility. It has no business
seeing your network, your credentials, or anything outside the folders you
point it at.

## What the app *never* does

- **No network calls.** The app does not contact any server — not ours, not
  Google's, not a telemetry collector. You can verify this by running it with
  the network disabled, or by auditing the imports (no `requests`, `urllib`,
  `socket`, etc. in any module under `app/`).
- **No telemetry, no analytics, no crash reporters.** No data leaves your
  computer.
- **No auto-updates.** New versions only arrive when *you* download them.
- **No background services.** The app only runs while its window is open.

## What the app *does* do

- Reads files under the **Source folder** you pick.
- Writes files under the **Destination folder** you pick.
- Reads EXIF metadata from images to name them chronologically.
- Computes cryptographic hashes (MD5, or xxHash if installed) of file
  contents to detect duplicates.
- In *Move* mode, deletes source files only after the destination copy has
  been hash-verified byte-for-byte. In *Copy* mode (default), originals are
  never touched.

## Reading the source

Every release on the GitHub **Releases** page is built by the public
`Build installer` GitHub Actions workflow from a specific commit in this
repository. You can:

1. Read the `app/` directory to audit what the program does.
2. Read `.github/workflows/release.yml` to see exactly how the installer is
   assembled — there is no hidden build step.
3. Rebuild it yourself: see *Run from source* in the README.

## Scanning with antivirus

You can upload the installer to <https://virustotal.com> for a multi-engine
scan. Results should be clean. If they are not, please open a GitHub issue
with the details.

## Windows SmartScreen notice

The installer is currently **unsigned** (commercial code-signing certificates
cost $100–400 per year). On first run, Windows SmartScreen may show:

> "Windows protected your PC"

Click **More info → Run anyway**. As the download count grows, SmartScreen's
reputation system will eventually stop warning.

A signed installer is planned for a future release.

## Reporting a vulnerability

Open a GitHub issue, or (for anything sensitive) email the maintainer listed
in the repository's profile.

## Dependencies

The app is built from source code in `app/` plus these upstream Python
packages, all installable from PyPI:

| Package     | Purpose                                  |
|-------------|------------------------------------------|
| PyQt6       | Desktop UI (Qt 6 bindings)               |
| rapidfuzz   | String-similarity scoring                |
| Pillow      | EXIF extraction for JPEG/PNG/TIFF        |
| exifread    | EXIF extraction fallback for RAW         |
| xxhash      | Fast non-cryptographic hashing           |

You can audit every line of our code under `app/`. The release workflow
pins each dependency version in `requirements.txt`.
