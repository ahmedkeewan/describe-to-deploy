# [Spike] One-click macOS installer for the harness

> **Outcome:** superseded. The one-click path that shipped is the `.mcpb` Claude Desktop bundle
> ([`mcpb/`](../../../mcpb/README.md)); no `.pkg` installer was built. Kept as a record of the
> investigation ([issue #76](https://github.com/ahmedkeewan/service-buddy/issues/76)).

**Disposition at the time: PROMOTE, with named blockers before a real build.**

## Hypothesis

A one-click packaged installer for macOS can bundle Docker/Floci/MCP wiring behind a GUI, so a
non-technical founder never sees a terminal to actually use this harness on their own product.

## What was tested

macOS's native packaging tools (`pkgbuild`, `productbuild`, `installer`) are present on a
standard macOS install with no extra tooling required. A minimal `.pkg` was built locally with
`pkgbuild --nopayload --scripts <dir> ...`, embedding a `postinstall` shell script. Expanding the
built package with `pkgutil --expand` (read-only, no execution) confirmed the script is embedded
exactly as authored and would run as part of a standard Installer.app flow.

**Not tested**: actually double-clicking the package and completing a real install. Running
`sudo installer` (an admin-privileged install) was out of scope for the spike, so the full
end-to-end GUI flow — the native Continue/License/Install screens, the password prompt, and the
postinstall script's real execution — was not exercised.

## Answer to the hypothesis

**Yes, technically viable, with real costs to name:**

1. **Mechanism confirmed**: a `.pkg` file with a `postinstall` script is the right shape. Apple's
   Installer.app provides the entire GUI (license screen, Install button, admin password prompt)
   natively — the user never opens a terminal, and the password prompt is a native macOS dialog,
   not a terminal login.
2. **Signing/notarization is a real, named blocker for actual distribution.** An unsigned `.pkg`
   triggers Gatekeeper's "unidentified developer" warning on any machine other than the one that
   built it. Real distribution needs an Apple Developer ID ($99/year) and notarization — a cost
   and process this spike did not attempt.
3. **Progress-visibility UX gap.** The real install would need the postinstall script to actually
   run `setup.sh`'s underlying steps (Homebrew install/check, Docker/Colima install, MCP config
   wiring) — a multi-minute, network-dependent sequence. Installer.app's own progress bar is
   generic and gives no per-step feedback; a founder watching a silent progress bar for several
   minutes is a worse experience than `setup.sh`'s own printed steps today. A production version
   should budget for either a custom installer plugin pane, or a small companion app with a real
   progress window, not a bare `.pkg`.
4. **The heavy dependency (Docker/Colima) doesn't go away.** This installer removes the terminal,
   not the actual disk/CPU/network cost of installing Docker Desktop or Colima — that's still a
   real, sometimes slow step happening behind the scenes.

## Recommendation

Promote to a full feature ticket, scoped to:
- A real postinstall script performing `setup.sh`'s actual steps (not this spike's
  logging-only proof of concept).
- An Apple Developer ID + notarization pipeline (a prerequisite, likely its own small ticket).
- A decision on progress-visibility UX (custom installer pane vs. companion progress app) —
  worth a quick round of user feedback before committing to either.
- **Scope stays macOS-only**, per the original ticket's decision — Windows/WSL and Linux remain
  out of scope until this spike's macOS path is proven in a real install.

## Artifacts

- Issue: [#76](https://github.com/ahmedkeewan/service-buddy/issues/76)
- This spike's test package and logs were built and inspected locally, then deleted — nothing
  from this spike ships in the repo except this memo.
