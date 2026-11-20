import contract from "./checkout-contract.js";
import { boneProfile, applyBoneProfile } from "./vendor/checkout-bones.js";
export { CHECKOUT_ANATOMY } from "./checkout-anatomy.js";
export { contract };
const plain = (v) => !!v && Object.getPrototypeOf(v) === Object.prototype;
const keys = (v, allowed) => {
  if (!plain(v) || Object.keys(v).some((k) => !allowed.includes(k)))
    throw Error("Propiedad de diseño no permitida");
};
const lengths = (v, rules) => {
  keys(v, Object.keys(rules));
  for (const [k, n] of Object.entries(v)) {
    const [lo, hi] = rules[k];
    if (typeof n !== "number" || !Number.isFinite(n) || n < lo || n > hi)
      throw Error("Medida fuera del límite: " + k);
  }
  return { ...v };
};
export function checkoutProfile(input) {
  keys(input, [
    "schema_version",
    "layout",
    "geometry",
    "typography",
    "colors",
    "bones",
  ]);
  if (
    input.schema_version !== "1" ||
    !["sidebar", "stacked"].includes(input.layout)
  )
    throw Error("Versión o distribución no compatible");
  const geometry = lengths(input.geometry || {}, contract.geometry),
    type = input.typography || {};
  keys(type, [...Object.keys(contract.typography), "bodyFont", "headingFont"]);
  const numeric = Object.fromEntries(
    Object.entries(type).filter(([k]) => !k.endsWith("Font")),
  );
  lengths(numeric, contract.typography);
  for (const k of ["bodyFont", "headingFont"])
    if (type[k] !== undefined && !Object.hasOwn(contract.fonts, type[k]))
      throw Error("Fuente no disponible");
  const colors = input.colors || {};
  keys(colors, contract.colors);
  for (const v of Object.values(colors))
    if (typeof v !== "string" || !/^#[a-f0-9]{6}$/i.test(v))
      throw Error("Color no válido");
  keys(input.bones || {}, ["surfaces"]);
  const surfaces = input.bones?.surfaces || {};
  keys(surfaces, contract.surfaces);
  // The shared bones validator owns lengths/colors; opacity is deliberately absent here.
  for (const v of Object.values(surfaces))
    keys(v, [
      "radius",
      "fill",
      "borderWidth",
      "borderColor",
      "padding",
      "marginTop",
      "marginBottom",
      "shadow",
    ]);
  const bones = boneProfile({ surfaces });
  return {
    schema_version: "1",
    layout: input.layout,
    geometry,
    typography: { ...type },
    colors: { ...colors },
    bones: { surfaces: bones.surfaces },
  };
}
export const preset = (name) =>
  checkoutProfile(
    structuredClone(contract.presets[name] || contract.presets.source),
  );
export function applyCheckoutProfile(host, input) {
  const p = checkoutProfile(input); // Validate before touching the DOM: failed imports preserve the current profile.
  for (const key of [
    ...Object.keys(contract.geometry),
    ...Object.keys(contract.typography),
    ...contract.colors,
    "bodyFont",
    "headingFont",
  ])
    host.style.removeProperty("--cx-" + key);
  for (const [k, v] of Object.entries(p.geometry))
    host.style.setProperty("--cx-" + k, v + "px");
  for (const [k, v] of Object.entries(p.colors))
    host.style.setProperty("--cx-" + k, v);
  for (const [k, v] of Object.entries(p.typography))
    host.style.setProperty(
      "--cx-" + k,
      k.endsWith("Font") ? contract.fonts[v] : v + "px",
    );
  host.style.removeProperty("--cx-rowTarget");
  if (p.typography.actionSize) host.style.setProperty("--cx-rowTarget", "44px");
  applyBoneProfile(host, p.bones);
  host.dataset.checkoutLayout = p.layout;
  host.dispatchEvent(
    new host.ownerDocument.defaultView.CustomEvent("101:checkout-design", {
      detail: p,
    }),
  );
  return p;
}
// Same module serves the normal customer route and the authenticated editor iframe.
if (
  typeof document !== "undefined" &&
  document.body?.hasAttribute("data-checkout-chassis")
) {
  const host = document.body,
    query = new URLSearchParams(location.search),
    business = query.get("business_id") || host.dataset.commerceBusiness;
  const preview =
    query.get("checkout_preview") === "1" && window.parent !== window;
  window.CheckoutChassis = {
    preview,
    apply: (input) => applyCheckoutProfile(host, input),
  };
  fetch(
    "/api/restaurants/" + encodeURIComponent(business) + "/checkout-design",
    { cache: "no-store" },
  )
    .then((r) => (r.ok ? r.json() : Promise.reject()))
    .then((v) => {
      applyCheckoutProfile(host, v.profile);
    })
    .catch(() => applyCheckoutProfile(host, preset("source")))
    .finally(() => {
      host.dataset.checkoutReady = "true";
      if (preview)
        window.parent.postMessage(
          { type: "101:checkout-ready", business_id: business },
          location.origin,
        );
    });
  if (preview) {
    host.dataset.checkoutPreview = "true";
    window.addEventListener("message", (e) => {
      if (
        e.origin !== location.origin ||
        e.source !== window.parent ||
        e.data?.type !== "101:checkout-preview" ||
        e.data.business_id !== business
      )
        return;
      try {
        applyCheckoutProfile(host, e.data.profile);
      } catch {
        /* No change on invalid preview. */
      }
    });
  }
}
