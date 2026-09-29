const VALID_TABS = ["search", "lookup", "browse"];
const ROUTE_PATHS = { research: "/", cite: "/cite" };
const PATH_ROUTES = Object.fromEntries(
  Object.entries(ROUTE_PATHS).map(([route, path]) => [path, route]),
);

function routeFromPath(pathname) {
  const path = pathname.replace(/\/+$/, "") || "/";
  return PATH_ROUTES[path] || "research";
}

function tabFromSearch(search) {
  const tab = new URLSearchParams(search).get("tab");
  return VALID_TABS.includes(tab) ? tab : "search";
}

function currentUrl() {
  const base = ROUTE_PATHS[router.route] || "/";
  if (router.route === "research" && router.tab !== "search") {
    return `${base}?tab=${router.tab}`;
  }
  return base;
}

export const router = $state({
  route: routeFromPath(window.location.pathname),
  tab: tabFromSearch(window.location.search),
});

export function navigate(route) {
  if (!(route in ROUTE_PATHS) || route === router.route) return;
  router.route = route;
  router.tab = "search";
  window.history.pushState(null, "", ROUTE_PATHS[route]);
}

export function setTab(tab) {
  if (!VALID_TABS.includes(tab) || tab === router.tab) return;
  router.tab = tab;
  window.history.replaceState(null, "", currentUrl());
}

export function initRouter() {
  const sync = () => {
    router.route = routeFromPath(window.location.pathname);
    router.tab = tabFromSearch(window.location.search);
  };
  window.addEventListener("popstate", sync);
  sync();
}
