import { router } from "./router.svelte.js";

export const MODE_LABELS = {
  fts: "Exact wording",
  hybrid: "Best match",
  vector: "Related concepts",
  research: "Research",
  precedent: "Precedent",
};

export const appContext = $state({
  search: null,
  lookup: null,
  cite: null,
  dismissed: { search: false, lookup: false, cite: false },
});

export function setSearch(value) {
  appContext.search = value;
  appContext.dismissed.search = false;
}

export function setLookup(value) {
  appContext.lookup = value;
  appContext.dismissed.lookup = false;
}

export function setCite(value) {
  appContext.cite = value;
  appContext.dismissed.cite = false;
}

export function dismissContext(key) {
  if (key in appContext.dismissed) appContext.dismissed[key] = true;
}

export function clearContext() {
  appContext.search = null;
  appContext.lookup = null;
  appContext.cite = null;
}

export function visibleContext() {
  return {
    search: appContext.search && !appContext.dismissed.search ? appContext.search : null,
    lookup: appContext.lookup && !appContext.dismissed.lookup ? appContext.lookup : null,
    cite: appContext.cite && !appContext.dismissed.cite ? appContext.cite : null,
  };
}

const ROUTE_LABELS = { research: "Research", cite: "Cite" };

export function buildContextNote() {
  const { search, lookup, cite } = visibleContext();
  if (!search && !lookup && !cite) return null;

  const parts = [`Current screen: ${ROUTE_LABELS[router.route] || "Research"}.`];
  if (search) {
    let line = `Last search: "${search.query}" (${MODE_LABELS[search.mode] || search.mode})`;
    if (search.chapter) line += ` in chapter ${search.chapter}`;
    if (search.date) line += `, as at ${search.date}`;
    if (search.top?.section) {
      line += `. Top result: ${search.top.title || "untitled"}, ${search.top.chapter}, s. ${search.top.section}`;
    }
    parts.push(line + ".");
  }
  if (lookup) {
    parts.push(
      `Viewing provision: ${lookup.title || "untitled"}, ${lookup.chapter}, s. ${lookup.section}` +
        `${lookup.date ? `, as at ${lookup.date}` : ""}.`,
    );
  }
  if (cite) {
    parts.push(
      `Validated citation (${cite.status}): ${cite.title || "untitled"}, ${cite.chapter}, s. ${cite.section}` +
        `${cite.date ? `, as at ${cite.date}` : ""}.`,
    );
  }
  return `(Context from the user's current screen — use only if relevant to the question.) ${parts.join(" ")}`;
}
