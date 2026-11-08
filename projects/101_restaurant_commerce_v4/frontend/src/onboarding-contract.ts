/** CSV input boundary. Ownership and provisioning authority remain on the server. */
export type BusinessDraft = {
  name: string;
  slug: string;
  custom_hostname?: string;
};
export function parseBusinesses(text: string): BusinessDraft[] {
  const rows: string[][] = [];
  let row: string[] = [],
    cell = "",
    quoted = false,
    closed = false;
  for (let i = 0; i <= text.length; i++) {
    const c = text[i] ?? "\n";
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') {
        cell += '"';
        i++;
      } else if (c === '"') {
        quoted = false;
        closed = true;
      } else if (i === text.length) throw Error("Hay comillas sin cerrar.");
      else cell += c;
    } else if (c === '"') {
      if (cell.trim() || closed)
        throw Error("Revisa las comillas del archivo.");
      cell = "";
      quoted = true;
    } else if (c === "," || c === "\n") {
      row.push(cell.trim());
      cell = "";
      closed = false;
      if (c === "\n") {
        if (row.some(Boolean)) rows.push(row);
        row = [];
      }
    } else if (closed && c.trim())
      throw Error("Separa las columnas con una coma.");
    else cell += c;
  }
  if (
    rows[0]?.[0].toLowerCase() === "nombre" &&
    rows[0]?.[1].toLowerCase() === "enlace"
  )
    rows.shift();
  if (!rows.length || rows.length > 100)
    throw Error("Incluye entre 1 y 100 negocios.");
  const slugs = new Set<string>(),
    hosts = new Set<string>();
  return rows.map((cells, i) => {
    const [name, slug, domain = ""] = cells;
    if (
      cells.length < 2 ||
      cells.length > 3 ||
      !name ||
      name.length > 200 ||
      !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug) ||
      slug.length < 2 ||
      slug.length > 50
    )
      throw Error(
        `Línea ${i + 1}: revisa nombre y enlace (2–50 letras minúsculas, números o guiones).`,
      );
    const host = domain.toLowerCase().replace(/\.$/, "");
    if (
      host &&
      (host.length > 253 ||
        !host.includes(".") ||
        host
          .split(".")
          .some((p) => !/^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(p)))
    )
      throw Error(
        `Línea ${i + 1}: escribe un dominio sin https, rutas ni puertos.`,
      );
    if (slugs.has(slug) || (host && hosts.has(host)))
      throw Error(`Línea ${i + 1}: enlace o dominio repetido.`);
    slugs.add(slug);
    if (host) hosts.add(host);
    return { name, slug, ...(host ? { custom_hostname: host } : {}) };
  });
}
export function csvCell(value: string) {
  return '"' + value.replaceAll('"', '""') + '"';
}
