import { build } from "esbuild";
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync, mkdirSync, readdirSync } from "node:fs";
const original = JSON.parse(
  readFileSync("vendor/react-email/manifest.json", "utf8"),
);
for (const [name, digest] of Object.entries(original.files)) {
  if (
    createHash("sha256")
      .update(readFileSync("vendor/react-email/" + name))
      .digest("hex") !== digest
  )
    throw new Error("Pinned upstream source changed: " + name);
}
const out = new URL(
  "../../src/world_model/restaurant_commerce/email_runtime/",
  import.meta.url,
);
mkdirSync(out, { recursive: true });
await build({
  entryPoints: ["src/cli.tsx"],
  bundle: true,
  platform: "node",
  format: "cjs",
  target: "node22",
  jsx: "automatic",
  outfile: new URL("renderer.cjs", out).pathname,
  minify: true,
  legalComments: "eof",
  metafile: true,
});
const hash = (b) => createHash("sha256").update(b).digest("hex");
const bundle_sha256 = hash(readFileSync(new URL("renderer.cjs", out)));
const assets = Object.fromEntries(
  readdirSync(new URL("fonts/", out))
    .sort()
    .map((n) => [n, hash(readFileSync(new URL("fonts/" + n, out)))]),
);
const renderer_sha256 = hash(
  bundle_sha256 +
    Object.entries(assets)
      .map(([k, v]) => k + ":" + v)
      .join("|"),
);
writeFileSync(
  new URL("manifest.json", out),
  JSON.stringify(
    {
      schema_version: "1",
      protocol: "101-email-json-v1",
      bundle_sha256,
      assets,
      renderer_sha256,
      templates: [
        "classic",
        "barebone",
        "matte",
        "protocol",
        "arcane",
        "studio",
      ],
      template_version: "1",
      upstream_commit: "beda35bb12cad36c202534601591cc98c651c8c9",
      package: JSON.parse(readFileSync("package.json", "utf8")).dependencies[
        "react-email"
      ],
    },
    null,
    2,
  ) + "\n",
);

// Retain full notices for the pinned dependency set alongside esbuild's legal comments.
const lock = JSON.parse(readFileSync("package-lock.json", "utf8"));
let notices = readFileSync("vendor/react-email/LICENSE.md", "utf8") + "\n";
for (const [name, meta] of Object.entries(lock.packages)) {
  if (!name.startsWith("node_modules/")) continue;
  for (const file of [
    "LICENSE",
    "LICENSE.md",
    "LICENSE.txt",
    "license",
    "license.md",
    "COPYING",
  ]) {
    try {
      notices +=
        "\n--- " +
        name +
        "@" +
        meta.version +
        " ---\n" +
        readFileSync(
          new URL(
            "../node_modules/" + name.slice(13) + "/" + file,
            import.meta.url,
          ),
          "utf8",
        );
      break;
    } catch {}
  }
}
writeFileSync(new URL("THIRD_PARTY_NOTICES.txt", out), notices.split(/\r?\n/).map(line=>line.trimEnd()).join("\n"));
