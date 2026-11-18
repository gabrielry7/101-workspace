import { strict as assert } from "node:assert";
import { test } from "node:test";
import { renderEmail } from "./index";
import { fixture } from "./fixture";
import { templateIds } from "./contract";

test("all six designs preserve the same escaped message and useful links", async () => {
  const html = new Set<string>();
  for (const template_id of templateIds) {
    const result = await renderEmail({
      ...fixture,
      template_id,
      content: {
        ...fixture.content,
        title: "Una nota específica",
        body: "Texto <script>alert(1)</script>\n\nInformación confirmada.",
      },
    });
    assert.match(result.html, /&lt;script&gt;/);
    assert.ok(!result.html.includes("<script>"));
    assert.ok(result.text.includes("Una nota específica"));
    assert.ok(result.text.includes("Información confirmada."));
    assert.ok(result.text.includes(fixture.personalization.unsubscribe_url));
    assert.ok(!result.text.includes("SKIN15"));
    html.add(result.html);
  }
  assert.equal(html.size, 6);
});

test("untrusted renderer instructions and unsafe URLs are rejected", async () => {
  await assert.rejects(renderEmail({ ...fixture, command: "arbitrary" }));
  await assert.rejects(
    renderEmail({
      ...fixture,
      media: { url: "javascript:alert(1)", alt: "x" },
    }),
  );
  await assert.rejects(
    renderEmail({
      ...fixture,
      content: { ...fixture.content, body: "bad\u0000text" },
    }),
  );
});
