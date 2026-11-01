# LiveContainer + SideStore Nightly-only Source

This is a **community-created source generator**, not an official LiveContainer source.

1. Create a public GitHub repository and upload the files, preserving `.github/workflows/update.yml` and `scripts/update.py`.
2. Under **Settings → Actions → General → Workflow permissions**, allow **Read and write permissions**.
3. Open **Actions → Update combined Nightly source → Run workflow**.
4. If an official combined Nightly IPA is attached to the `nightly` release, `apps.json` is generated. Add this URL to SideStore Sources:

   `https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/apps.json`

5. If the Nightly release has **no** `LiveContainer+SideStore.ipa`, the workflow leaves the existing source unchanged and **never** substitutes a stable IPA. On initial setup, `apps.json` will not exist until a combined Nightly IPA is published.

The source's version is read from the IPA's `Info.plist` to match SideStore update detection. The workflow checks every six hours. This is not an official auto-update mechanism, and installation compatibility is not guaranteed.
