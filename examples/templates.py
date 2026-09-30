"""Create a template, edit it, walk its version history, publish and delete it.

Run:
    TRATTO_API_KEY=tratto_test_... python examples/templates.py
"""

import os

from tratto import CreateTemplateOptions, Tratto, UpdateTemplateOptions

api_key = os.environ.get("TRATTO_API_KEY")
if not api_key:
    raise SystemExit("Set the TRATTO_API_KEY environment variable")

tratto = Tratto(api_key)

# ── 1. Create — templates start as drafts ─────────────────────────────────────
template = tratto.templates.create(
    CreateTemplateOptions(
        name="Welcome email",
        html="<h1>Hi {{first_name}}</h1><p>Welcome to {{product}}.</p>",
    )
)
template_id = template["id"]
print("created", template_id)

# Or write it in emailmd markdown and let the API render the HTML.
markdown_template = tratto.templates.create(
    CreateTemplateOptions(
        name="Monthly digest",
        markdown="# Hi {{first_name}}\n\nHere is what happened this month.\n",
    )
)

# ── 2. Update — changing the body creates a new version ───────────────────────
tratto.templates.update(
    template_id,
    UpdateTemplateOptions(html="<h1>Hello {{first_name}}</h1><p>Glad you are here.</p>"),
)

# ── 3. Version history (most recent first, up to 20) ──────────────────────────
versions = tratto.templates.list_versions(template_id)["data"]
for version in versions:
    print(" v", version["version"], version["createdAt"])

previous = tratto.templates.get_version(template_id, versions[-1]["version"])
print("first version was", len(previous["html"]), "bytes")

# ── 4. Publish, so campaigns can use it ───────────────────────────────────────
tratto.templates.update(template_id, UpdateTemplateOptions(status="published"))
print("status:", tratto.templates.get(template_id)["status"])


def preview_in_your_own_inbox(template_id: str) -> None:
    """Not called here: a test send reaches a real inbox, so it needs a live
    key. A test key is rejected with 403 TEST_MODE_NOT_SUPPORTED.
    """
    tratto.templates.test_send(template_id, "you@acme.com", {"first_name": "Alice"})


# ── 5. List and clean up ──────────────────────────────────────────────────────
published = tratto.templates.list(status="published", limit=25)
print("published templates:", len(published["data"]))

# Deleting is permanent and takes the version history with it.
tratto.templates.delete(markdown_template["id"])
