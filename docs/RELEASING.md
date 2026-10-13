# Releasing

1. Bump `SLOPPY_VERSION` in `compiler/main.jo` (and `version` in `editors/vscode/package.json`
   when the extension changed: the stores skip a version they already have), add the version's
   section to `CHANGELOG.md` (it becomes the release notes), commit, push.
2. `git tag vX.Y.Z && git push origin vX.Y.Z`.

`.github/workflows/release.yml` then builds and tests everything, makes the GitHub release
(tarballs for Linux on x86-64 and arm64 and for macOS, the Windows zip, checksums, the editor extension's .vsix), and publishes the
extension to the VS Code Marketplace and Open VSX.

Publishing the extension needs no stored tokens: the workflow's GitHub OIDC token is exchanged
for short-lived ones. Both are set up (as below). The publishing job runs
in the GitHub environment `marketplace-publish` (Settings → Environments: it can be limited to
`v*` tags there, so nothing else can publish).

To publish an existing release's extension again (after setting a store up, say): Actions →
Release → Run workflow, with the tag.

## VS Code Marketplace (an Azure managed identity)

Once (an Azure account is needed; the free tier is enough, nothing here costs anything):

1. Azure portal → **Managed Identities** → **Create**: any subscription, resource group and
   region; name it e.g. `sloppy-marketplace`.
2. On the new identity: **Settings → Federated credentials → Add credential**:
   scenario **GitHub Actions deploying Azure resources**, organization `david-andrew`
   (organization ID `41205753`), repository `sloppy-lang` (repository ID `1410110127`), entity
   **Environment**, environment `marketplace-publish`, any name. Keep the generated subject: the
   repository's OIDC tokens use the form with IDs,
   `repo:david-andrew@41205753/sloppy-lang@1410110127:environment:marketplace-publish`. (IDs from
   `gh api repos/david-andrew/sloppy-lang --jq '.owner.id, .id'`.)
3. On the identity: **Settings → Properties**: copy the Client ID and Tenant ID into the
   repository's variables (Settings → Secrets and variables → Actions → Variables):
   `AZURE_CLIENT_ID` and `AZURE_TENANT_ID`. (They are not secrets.)
4. Actions → Release → Run workflow with **only print the Azure identity's Marketplace id**
   checked. The log of "The identity's Marketplace id" prints the id; copy it.
5. https://marketplace.visualstudio.com/manage → the RedFoxLabs publisher → **Members** → **Add**:
   paste that id, role **Contributor**.

From then on, releases publish to the Marketplace. (Done.) (Personal access tokens stop working for
the Marketplace on 1 December 2026; this does not use one.)

## Open VSX (trusted publishing)

Needs ownership of the RedFoxLabs namespace (being a contributor is not enough), a signed
publisher agreement, and the extension already there with at least one version.

https://open-vsx.org → Settings → **Trusted Publishers** → namespace RedFoxLabs →
**GitHub Actions**: owner `david-andrew`, repository `sloppy-lang`, workflow `release.yml`,
environment `marketplace-publish`. (Done: releases publish to Open VSX.)
