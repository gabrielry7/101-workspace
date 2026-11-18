import { strict as assert } from "node:assert";
import { test } from "node:test";
import { renderEmail } from "./index";
import { fixture } from "./fixture";
import { templateIds } from "./contract";
import { chassisSchema } from "./chassis";

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

test("one chassis applies to six recipes without changing copy, sources or destinations", async () => {
  const chassis = chassisSchema.parse({
    schema_version: "1",
    coat: "neutral",
    geometry: { maxWidth: 560 },
    bones: { surfaces: { controls: { radius: 12 }, content: { padding: 24 } } },
    typography: {
      heading: { fontSize: 24 },
      body: { fontFamily: "Georgia", color: "#123456" },
    },
  });
  for (const template_id of templateIds) {
    const source = await renderEmail({ ...fixture, template_id });
    const styled = await renderEmail({ ...fixture, template_id, chassis });
    assert.equal(source.text, styled.text);
    assert.ok(styled.html.includes('data-101-bone-role="heading"'));
    assert.ok(styled.html.includes("font-size:24px"));
    assert.ok(styled.html.includes("#123456"));
    assert.ok(styled.html.includes(fixture.personalization.unsubscribe_url));
  }
  for (const invalid of [
    { schema_version: "1", css: "display:none" },
    { schema_version: "1", bones: { surfaces: { footer: { opacity: 0 } } } },
    {
      schema_version: "1",
      typography: { body: { fontFamily: "url(unsafe)" } },
    },
  ])
    assert.throws(() => chassisSchema.parse(invalid));
});
