// Four actual old Admin anchors survived in bookmarks. Fragments are browser-only,
// so map them before React chooses a screen, without putting secrets in return URLs.
export function restoreLegacySection() {
  const sections: Record<string, { path: string; view?: string }> = {
    orderQueue: { path: "/workspace/sales", view: "orders" },
    availability: { path: "/workspace/settings" },
    financialSection: { path: "/workspace/sales", view: "reviews" },
    dailySection: { path: "/workspace/reports", view: "daily" },
  };
  const selected = sections[location.hash.slice(1)];
  if (!selected) return;
  const login = location.pathname === "/workspace/login",
    query = new URLSearchParams(location.search);
  const target = new URL(
    login ? query.get("next") || "/workspace/sales" : location.href,
    location.origin,
  );
  if (
    target.origin !== location.origin ||
    !["/admin", "/workspace/sales"].includes(target.pathname)
  )
    return;
  const business =
    target.searchParams.get("business") ||
    target.searchParams.get("business_id");
  target.searchParams.delete("business_id");
  if (business) target.searchParams.set("business", business);
  target.searchParams.delete("view");
  if (selected.view) target.searchParams.set("view", selected.view);
  const destination =
    selected.path + (target.searchParams.size ? "?" + target.searchParams : "");
  if (login) {
    query.set("next", destination);
    history.replaceState(null, "", location.pathname + "?" + query);
  } else history.replaceState(null, "", destination);
}
