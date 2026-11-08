# Social in the shared workspace

Social is registered by the normal `api.create_app`, rendered inside the existing
React shell at `/workspace/social`, and authorized by the same staff cookie,
membership and growth permissions used by Customers/Campaigns. No social-specific
account or business registry is introduced. Demo aliases remain explicitly limited
to development demo composition; they are not production credentials.

The provisioner creates the commerce profile with the canonical Business UUID as
its existing `business_id`. Social assets/packs reference that profile directly.
Historical free-form demo IDs stay historical; integration does not remap them.
Pack facts are owner-confirmed statements with sources/validity, not automatic
Genome promotion or new canonical Truth. Existing analytics remains intact.

## Existing database upgrade

Back up and verify the selected database and stop writers. Install the reviewed
commerce package and its declared Pillow dependency. Then run through the existing
maintenance owner (database URL comes from the private environment):

```sh
python -m world_model.restaurant_commerce.maintenance upgrade-social --offline
```

This additively creates `social_assets`, `social_packs`, `social_revisions`,
`social_approvals` and `social_uploads`; it is repeatable. It refuses incomplete
existing social tables rather than silently accepting an incompatible schema.
No contacts, orders, memberships, campaigns or provisioning records are replaced.
Startup does not silently install social tables into an existing database. An
authorized request receives a clear 503 until the upgrade is applied; unauthorized
requests still fail authorization first. No credentials are required for offline
coding or this migration. Configured Instagram independently requires the existing
`upgrade-connections` maintenance command and live provider qualification.

Rollback: stop writers and restore the previous application release; leave additive
social tables/data intact. If database restore is needed, retain/quarantine new
uploads and reconcile writes made since backup before restoring. Do not drop social
records or overwrite the separate demo database as an application rollback.

## Verification

`tests/test_social_workspace.py` exercises an existing workspace upgrade twice,
contact/campaign preservation, actual asset/render/approval/export, app restart
with the same staff session, and membership revocation. Run its PostgreSQL case
only with `SOCIAL_TEST_DISPOSABLE_POSTGRES_URL` pointing to an explicitly disposable
database: the fixture drops social tables to rehearse an old installation.
Missing configuration skips that one case, not a PostgreSQL qualification claim.

`tests/test_social_workspace_browser.py` logs into the combined workspace once,
creates/approves a post, navigates Customers/Sales/Campaigns, returns to the saved
post and downloads it. A multi-business account switching contexts must clear the
previous business's form, library and approval. Captures go to a temporary directory
unless `SOCIAL_BROWSER_EVIDENCE` explicitly selects an evidence destination.

The base repository's `tests/provisioning/test_social_workspace.py` exercises a
normally provisioned canonical business and owner across social and analytics,
including foreign-owner denial and membership revocation. This is synthetic
integration proof, not a live Instagram or Honorato creative approval.

Production hosting, current owner-approved material, stronger static design/copy,
video and publication/outcome learning remain on `docs/social/ROADMAP.md` in the
base repository. The existing public social preview stays independently configured
until a shared deployment is explicitly verified.
