# Dependency maintenance

## Scope and decisions (2026-10-27)

The fresh main-branch `npm ci` audit reported **seven affected package entries: four moderate and three high**. The 2026-10-24 report had eleven; advisory ranges changed in the registry. Counts are affected packages, not independent vulnerabilities or evidence of exploitation.

| Finding | Application exposure and decision |
| --- | --- |
| Vite 7.3.6 (high) | Development server/file serving/editor integration. Update to 7.3.7 within Vite 7; do not expose the development server as a production service. |
| Vitest / mocker 4.1.11 (moderate) | Test tooling, not the shipped browser bundle. Update to 4.1.12 within Vitest 4. |
| source-map-js 1.2.1 (high) | PostCSS build dependency. Update to 1.2.2 through the existing range. |
| postcss-selector-parser (moderate) | Tailwind/PostCSS build dependency. Update to the compatible 6.1.5 patch; no Tailwind major migration or override. |
| Typography plugin (moderate through its pinned parser) | Unused: the Tailwind configuration has no plugins and the app has no prose classes. Remove it instead of the audit tool's suggested downgrade. |
| Zod 3 (high) | Declared but never imported. Registration uses controlled inputs, explicit password matching and backend serializers, not Zod. Remove Zod and the unused resolver adapter; do not migrate working forms to another major version. |

The Lovable development tagger and existing design system remain in place. No `npm audit fix --force`, vulnerability exclusion or package override is used. Registry audits do not establish backend dependency safety, historical secret absence, live-provider correctness or production readiness.

## Verification and ongoing checks

The updated lockfile audit reports **zero known npm vulnerabilities** on 2026-10-27, including development dependencies. `npm ci` and `make check` pass: 12 backend tests, six frontend behavior tests (password mismatch, search success/failure and failed-save recovery), Django/migration checks, TypeScript, lint and build. Three pre-existing lint warnings remain. Generated production CSS is byte-identical to the baseline.

npm 10.9.8 hit an internal `edgesOut` resolver error while updating Vitest's optional peer graph. The lockfile was generated with installed npm 11.16.0 on Node 22.23.1, then installed successfully with npm 10.9.8. No legacy-peer-deps flag, special npm configuration or newer npm requirement is needed to run the application.


From the repository root, `make check` remains the canonical behavioral validation. After dependency edits, also run `npm --prefix frontend ci` and `npm --prefix frontend audit --audit-level=moderate`. The audit includes development dependencies and needs registry access; unavailable registry data is a failed check, not a clean audit. Review current output rather than treating this dated snapshot as a permanent guarantee.

PR CI keeps the existing backend/frontend tests and build, audits the complete installed npm tree at moderate severity, and reviews newly introduced dependency advisories at moderate severity with read-only permissions. The two checks cover different cases: the audit catches newly published advisories in unchanged npm packages; PR review checks manifest changes, including Python requirements. Python packages are not installed/resolved by npm audit, and this PR does not claim a complete Python audit. Dependency graph/standard alerts must be enabled for dependency review.

Dependabot checks npm, pip and Actions weekly. Compatible npm/Python changes are grouped, with open version-update PR limits of two/one/one respectively; security-update limits are separate GitHub policy. Updates require review and passing checks; no auto-merge is configured. These settings take effect from the default branch after human merge.

References: [GitHub dependency review](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/manage-your-dependency-security/configure-dependency-review-action), [Dependabot configuration](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference), and the live npm audit advisory links. Remaining portfolio work is tracked in issue #6.
