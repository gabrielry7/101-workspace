import { CheckoutDesignView } from "./checkout-design";
import { restoreLegacySection } from "./legacy-section";
import { SignupContent, SignupTools } from "./signup-tools";
import { Catalog, CustomerSections } from "./growth-workspace";
import { ChannelConnections } from "./channel-config";
import { ReportsWorkspace } from "./daily-finance";
import { OperationSettingsView } from "./operation-settings";
import React, { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { Dialog } from "@base-ui/react/dialog";
import { CSPProvider } from "@base-ui/react/csp-provider";
import {
  House,
  ChartNoAxesColumnIncreasing,
  Palette,
  ArrowDownToLine,
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Copy,
  ExternalLink,
  Globe2,
  LogOut,
  Layers as LayersIcon,
  Mail,
  Megaphone,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  MessageCircle,
  Phone,
  Plug,
  QrCode,
  Search,
  ShoppingBag,
  SlidersHorizontal,
  Users,
  X,
} from "lucide-react";
import "./style.css";
import "./readability.css";
import {
  api,
  endpoint,
  date,
  amount,
  count,
  label,
  source,
  Avatar,
  useResource,
  Failure,
  Loading,
  type Customer,
} from "./ui";
import { SalesWorkspace } from "./sales";
import { WorkspaceEntry } from "./workspace-entry";
import { LoyaltyWorkspace } from "./loyalty";
import {
  HomeView,
  AnalyticsView,
  IdentityView,
  periodQuery,
} from "./workspace-views";
import { CampaignWorkspace } from "./campaign-workspace";
import { InstagramCallback } from "./social-instagram";
import { SocialWorkspace } from "./social";
import { ColorPreview } from "./color-preview";
import { OnboardingView } from "./onboarding";
const screenFromPath = () => {
  const path = location.pathname.split("/").pop() || "home";
  return [
    "reports",
    "sales",
    "customers",
    "campaigns",
    "analytics",
    "identity",
    "onboarding",
    "social",
    "login",
    "settings",
    "connections",
    "website",
  ].includes(path)
    ? path
    : "home";
};
const screenNames: Record<string, string> = {
  home: "Inicio",
  reports: "Reportes",
  sales: "Ventas",
  customers: "Clientes",
  campaigns: "Campañas",
  social: "Contenido",
  analytics: "Analítica web",
  identity: "Identidad",
  onboarding: "Negocios",
  settings: "Ajustes",
  connections: "Conexiones",
  website: "Sitio web",
};

type Business = {
  business_id: string;
  name: string;
  slug: string;
  role: string;
  permissions: string[];
};
type Identity = {
  username: string;
  csrf: string;
  businesses: Business[];
  platform_admin: boolean;
  actor_id: string;
};
type Listing = {
  items: Customer[];
  count: number;
  total: number;
  registered: number | null;
  offset: number;
  limit: number;
};
type Detail = Customer & {
  membership: null | {
    source: string;
    created_at: string;
    channel: string;
    scope: string;
  };
  permissions: {
    channel: string;
    scope: string;
    state: string;
    source: string;
    reason: string | null;
    at: string;
  }[];
  permission_available: boolean;
  orders: {
    id: string;
    code: string;
    created_at: string;
    status: string;
    payment_status: string;
    total_minor: number;
    currency: string;
    identity_verified: boolean;
  }[];
  order_count: number;
  money: {
    scope: string;
    currency: string;
    paid_orders: number;
    captured_minor: number;
    refunded_minor: number;
    net_minor: number;
  }[];
};
function Login({ onLogin }: { onLogin: (id: Identity) => void }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <div className="login">
      <div className="wordmark">
        101<span>workspace</span>
      </div>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError("");
          const form = new FormData(e.currentTarget);
          try {
            await api("/api/staff/login", {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                "X-101-Login": "1",
              },
              body: JSON.stringify({
                username: form.get("username"),
                password: form.get("password"),
              }),
            });
            onLogin(await api("/api/staff/me"));
          } catch {
            setError(
              "No pudimos iniciar sesión. Revisa tus datos e inténtalo de nuevo.",
            );
          } finally {
            setBusy(false);
          }
        }}
      >
        <h1>Iniciar sesión</h1>
        <label>
          Usuario
          <input name="username" autoComplete="username" required autoFocus />
        </label>
        <label>
          Contraseña
          <input
            name="password"
            type="password"
            autoComplete="current-password"
            required
          />
        </label>
        {error && (
          <p role="alert" className="form-error">
            {error}
          </p>
        )}
        <button className="button primary" disabled={busy}>
          {busy ? "Entrando…" : "Entrar"}
          <ArrowRight size={17} />
        </button>
      </form>
    </div>
  );
}
function App() {
  const [identity, setIdentity] = useState<Identity | null | undefined>();
  const authGeneration = useRef(0);
  const [authError, setAuthError] = useState("");
  const [params, setParams] = useState(
    () => new URLSearchParams(location.search),
  );
  const [screen, setScreen] = useState(screenFromPath());
  const routeMemory = useRef<Record<string, string>>({});
  const routeScroll = useRef<Record<string, number>>({});
  const [menu, setMenu] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    try {
      return localStorage.getItem("101-sidebar-collapsed") === "true";
    } catch {
      return false;
    }
  });
  const sidebarClose = useRef<HTMLButtonElement>(null);
  const sidebarOpen = useRef<HTMLButtonElement>(null);
  const sidebarFocusPending = useRef(false);
  useLayoutEffect(() => {
    if (sidebarFocusPending.current) {
      sidebarFocusPending.current = false;
      (sidebarCollapsed ? sidebarOpen : sidebarClose).current?.focus();
    }
  }, [sidebarCollapsed]);
  function toggleSidebar(collapsed: boolean) {
    sidebarFocusPending.current = true;
    setSidebarCollapsed(collapsed);
    try {
      localStorage.setItem("101-sidebar-collapsed", String(collapsed));
    } catch {
      /* optional preference */
    }
  }
  const [qr, setQr] = useState(
    new URLSearchParams(location.search).get("invite") === "1",
  );
  const [policy, setPolicy] = useState<{
    demo_mode: boolean;
    internal_tools: boolean;
  }>();
  const [search, setSearch] = useState(params.get("q") || "");
  const scrollRef = useRef(0);
  const returnFocus = useRef<HTMLAnchorElement | null>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const previousCustomer = useRef(params.get("customer"));
  const refreshIdentity = () => {
    const generation = ++authGeneration.current;
    setAuthError("");
    api<Identity>("/api/staff/me")
      .then((value) => {
        if (generation === authGeneration.current) setIdentity(value);
      })
      .catch((e) => {
        if (generation !== authGeneration.current) return;
        if (e.status === 401) setIdentity(null);
        else setAuthError(e.message);
      });
  };
  useEffect(() => {
    refreshIdentity();
    api<{ demo_mode: boolean; internal_tools: boolean }>("/api/browser-policy")
      .then(setPolicy)
      .catch(() => {});
    const pop = () => {
      setScreen(screenFromPath());
      setParams(new URLSearchParams(location.search));
      setSearch(new URLSearchParams(location.search).get("q") || "");
    };
    const expire = () => {
      ++authGeneration.current;
      setIdentity(null);
      routeMemory.current = {};
      routeScroll.current = {};
    };
    const sessionChanged = (event: StorageEvent) => {
      if (event.key === "101-session-ended") expire();
    };
    const visible = () => {
      if (!document.hidden) refreshIdentity();
    };
    const restored = (event: PageTransitionEvent) => {
      if (event.persisted) refreshIdentity();
    };
    document.addEventListener("visibilitychange", visible);
    window.addEventListener("pageshow", restored);
    window.addEventListener("popstate", pop);
    window.addEventListener("session-expired", expire);
    window.addEventListener("storage", sessionChanged);
    return () => {
      document.removeEventListener("visibilitychange", visible);
      window.removeEventListener("pageshow", restored);
      window.removeEventListener("popstate", pop);
      window.removeEventListener("session-expired", expire);
      window.removeEventListener("storage", sessionChanged);
    };
  }, []);
  useEffect(() => {
    if (
      identity?.platform_admin &&
      !identity.businesses.length &&
      screen !== "onboarding"
    ) {
      history.replaceState({}, "", "/workspace/onboarding" + location.search);
      setScreen("onboarding");
    }
  }, [identity, screen]);
  const requested = params.get("business");
  const business =
    identity?.businesses.find((b) => b.business_id === requested) ||
    (!requested && identity?.businesses.length === 1
      ? identity.businesses[0]
      : undefined);
  const bid = business?.business_id || "";
  const loyalty = screen === "customers" && params.get("view") === "loyalty";
  const catalogue =
    screen === "customers" &&
    ["promotions", "rewards"].includes(params.get("view") || "");
  const selected =
    loyalty || catalogue || params.get("view") === "signup"
      ? null
      : params.get("customer");
  const kind = params.get("kind") || "all";
  const offset = Math.max(0, Number(params.get("offset")) || 0);
  const query = params.get("q") || "";
  function navigate(changes: Record<string, string | null>, push = false) {
    const p = new URLSearchParams(location.search);
    for (const [k, v] of Object.entries(changes)) {
      if (v) p.set(k, v);
      else p.delete(k);
    }
    if (bid && !p.has("business")) p.set("business", bid);
    history[push ? "pushState" : "replaceState"](
      { customerWorkspace: true },
      "",
      `/workspace/${screen}${p.size ? "?" + p : ""}`,
    );
    setParams(p);
  }
  useEffect(() => {
    if (
      screen !== "customers" ||
      loyalty ||
      catalogue ||
      params.get("view") === "signup" ||
      search === query
    )
      return;
    const timer = setTimeout(
      () => navigate({ q: search.trim(), offset: null, customer: null }),
      180,
    );
    return () => clearTimeout(timer);
  }, [search, query, screen, loyalty, catalogue, params.get("view")]);
  const list = useResource<Listing>(
    bid &&
      screen === "customers" &&
      !loyalty &&
      !catalogue &&
      params.get("view") !== "signup"
      ? `${endpoint(bid)}/customers?q=${encodeURIComponent(query)}&kind=${encodeURIComponent(kind)}&offset=${offset}&limit=25&${periodQuery(params)}`
      : null,
  );
  useEffect(() => {
    if (!selected && previousCustomer.current) {
      requestAnimationFrame(() => {
        if (listRef.current) listRef.current.scrollTop = scrollRef.current;
        returnFocus.current?.focus({ preventScroll: true });
      });
    }
    previousCustomer.current = selected;
  }, [selected]);
  useEffect(() => {
    if (screen === "customers" && list.data)
      requestAnimationFrame(() => {
        if (listRef.current)
          listRef.current.scrollTop = routeScroll.current[bid + screen] || 0;
      });
  }, [screen, bid]);
  function selectCustomer(e: React.MouseEvent<HTMLAnchorElement>, id: string) {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    scrollRef.current = listRef.current?.scrollTop || 0;
    returnFocus.current = e.currentTarget;
    navigate({ customer: id }, true);
  }
  function closeDetail() {
    if (history.state?.customerWorkspace) history.back();
    else navigate({ customer: null });
  }
  async function endSession(all = false) {
    try {
      await api(all ? "/api/staff/logout-all" : "/api/staff/logout", {
        method: "POST",
        headers: { "X-101-CSRF": identity?.csrf || "" },
      });
      ++authGeneration.current;
      setIdentity(null);
      routeMemory.current = {};
      routeScroll.current = {};
      try {
        localStorage.setItem("101-session-ended", String(Date.now()));
      } catch {
        /* optional cross-tab notice */
      }
    } catch {
      setAuthError("No se pudo cerrar la sesión. Inténtalo de nuevo.");
    }
  }
  function goScreen(e: React.MouseEvent<HTMLAnchorElement>, target: string) {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    routeMemory.current[bid + screen] = location.search;
    if (screen === "customers")
      routeScroll.current[bid + screen] = listRef.current?.scrollTop || 0;
    const targetParams = new URLSearchParams(
      routeMemory.current[bid + target] || "",
    );
    targetParams.set("business", bid);
    for (const k of ["date_from", "date_to", "pairing"]) {
      const v = params.get(k);
      if (v) targetParams.set(k, v);
      else targetParams.delete(k);
    }
    history.pushState({}, "", `/workspace/${target}?${targetParams}`);
    setParams(targetParams);
    setSearch(targetParams.get("q") || "");
    setScreen(target);
    setMenu(false);
  }
  function nav(mobile = false) {
    return (
      <>
        <div className="business">
          <div>
            {identity && identity.businesses.length > 1 ? (
              <>
                <label
                  className="sr-only"
                  htmlFor={mobile ? "mobile-business" : "business"}
                >
                  Negocio
                </label>
                <select
                  id={mobile ? "mobile-business" : "business"}
                  title={business?.name}
                  value={bid}
                  onChange={(e) => {
                    setSearch("");
                    setQr(false);
                    navigate({
                      business: e.target.value,
                      q: null,
                      kind: null,
                      offset: null,
                      customer: null,
                      order: null,
                      campaign: null,
                      state: null,
                      status: null,
                      loyaltyId: null,
                      loyaltyEdit: null,
                      loyaltyVersion: null,
                      reservation: null,
                      reservation_status: null,
                      reservation_offset: null,
                      payment_status: null,
                      delivery: null,
                      delivery_status: null,
                      delivery_offset: null,
                      review_order: null,
                      finance_q: null,
                      finance_offset: null,
                      currency: null,
                      day: null,
                      conversation: null,
                      inbox_offset: null,
                      inbox_scope: null,
                      message_offset: null,
                      reply_offset: null,
                      outbox_offset: null,
                      outbox_status: null,
                      test_review: null,
                    });
                  }}
                >
                  {identity.businesses.map((b) => (
                    <option key={b.business_id} value={b.business_id}>
                      {b.name}
                    </option>
                  ))}
                </select>
              </>
            ) : (
              <strong title={business?.name}>
                {business?.name ||
                  (identity?.platform_admin
                    ? "Administración 101"
                    : "Selecciona un negocio")}
              </strong>
            )}
          </div>
          {!mobile && (
            <button
              ref={sidebarClose}
              type="button"
              className="icon-button sidebar-collapse"
              aria-label="Ocultar barra lateral"
              title="Ocultar barra lateral"
              aria-controls="workspace-sidebar"
              aria-expanded={true}
              onClick={() => toggleSidebar(true)}
            >
              <PanelLeftClose size={20} />
            </button>
          )}
        </div>
        {business && (
          <nav aria-label="Principal">
            <span className="nav-caption">ESPACIO DE TRABAJO</span>
            <a
              href={`/workspace/home?business=${bid}`}
              className={screen === "home" ? "active" : ""}
              aria-current={screen === "home" ? "page" : undefined}
              onClick={(e) => goScreen(e, "home")}
            >
              <House />
              Inicio
            </a>
            <a
              href={`/workspace/sales?business=${bid}`}
              className={screen === "sales" ? "active" : ""}
              aria-current={screen === "sales" ? "page" : undefined}
              onClick={(e) => goScreen(e, "sales")}
            >
              <ShoppingBag />
              Ventas
              <ExternalLink className="nav-external" />
            </a>
            <a
              className={screen === "customers" ? "active" : ""}
              aria-current={screen === "customers" ? "page" : undefined}
              href={`/workspace/customers?business=${bid}`}
              onClick={(e) => goScreen(e, "customers")}
            >
              <Users />
              Clientes
              {screen === "customers" && <span className="active-dot" />}
            </a>
            <a
              href={`/workspace/campaigns?business=${bid}`}
              className={screen === "campaigns" ? "active" : ""}
              aria-current={screen === "campaigns" ? "page" : undefined}
              onClick={(e) => goScreen(e, "campaigns")}
            >
              <Megaphone />
              Campañas
              <ExternalLink className="nav-external" />
            </a>
            <a
              href={`/workspace/analytics?business=${bid}`}
              className={screen === "analytics" ? "active" : ""}
              aria-current={screen === "analytics" ? "page" : undefined}
              onClick={(e) => goScreen(e, "analytics")}
            >
              <ChartNoAxesColumnIncreasing />
              Analítica web
            </a>
            <a
              href={`/workspace/reports?business=${bid}`}
              className={screen === "reports" ? "active" : ""}
              onClick={(e) => goScreen(e, "reports")}
            >
              <ChartNoAxesColumnIncreasing />
              Reportes
            </a>
            <details className="presence">
              <summary>
                <Globe2 />
                Presencia
                <ChevronDown size={14} />
              </summary>
              <div>
                <a href={`/workspace/website?business=${encodeURIComponent(bid)}`} onClick={(e) => goScreen(e, "website")} className={screen === "website" ? "active" : ""}>
                  Sitio web
                </a>
                <a
                  href={`/workspace/connections?business=${encodeURIComponent(bid)}&provider=google`}
                >
                  Google
                </a>
                <a
                  href={`/workspace/social?business=${bid}`}
                  onClick={(e) => goScreen(e, "social")}
                >
                  Instagram
                </a>
              </div>
            </details>
          </nav>
        )}
        <div className="nav-bottom">
          {identity?.platform_admin && (
            <a
              href="/workspace/onboarding"
              className={screen === "onboarding" ? "active" : ""}
              aria-current={screen === "onboarding" ? "page" : undefined}
              onClick={(e) => goScreen(e, "onboarding")}
            >
              <LayersIcon />
              Negocios
            </a>
          )}
          {business && (
            <>
              {policy?.internal_tools && (
                <a
                  href={`/workspace/identity?business=${bid}`}
                  onClick={(e) => goScreen(e, "identity")}
                >
                  <Palette />
                  Identidad
                </a>
              )}
              <a
                href={`/workspace/connections?business=${encodeURIComponent(bid)}&provider=google`}
                className={screen === "connections" ? "active" : ""}
                aria-current={screen === "connections" ? "page" : undefined}
                onClick={(e) => goScreen(e, "connections")}
              >
                <Plug />
                Conexiones
              </a>
              <a
                href={`/workspace/settings?business=${encodeURIComponent(bid)}`}
                onClick={(e) => goScreen(e, "settings")}
                className={screen === "settings" ? "active" : ""}
                aria-current={screen === "settings" ? "page" : undefined}
              >
                <SlidersHorizontal />
                Ajustes
              </a>
            </>
          )}
          <div className="account">
            <span className="account-avatar">
              {identity?.username.slice(0, 1).toUpperCase()}
            </span>
            <details
              className="account-security"
              onBlur={(e) => {
                if (!e.currentTarget.contains(e.relatedTarget as Node | null))
                  e.currentTarget.open = false;
              }}
              onKeyDown={(e) => {
                if (e.key === "Escape") {
                  e.currentTarget.open = false;
                  e.currentTarget.querySelector("summary")?.focus();
                }
              }}
            >
              <summary aria-label="Opciones de sesión">
                <strong>{identity?.username}</strong>
                <small>
                  {identity?.platform_admin
                    ? "Administrador 101"
                    : business?.role === "manager"
                      ? "Administrador"
                      : "Equipo"}
                </small>
              </summary>
              <div className="session-menu">
                <button
                  className="button secondary"
                  onClick={() => endSession(true)}
                >
                  Cerrar todas mis sesiones
                </button>
              </div>
            </details>
            <button
              className="icon-button"
              aria-label="Cerrar sesión"
              onClick={() => endSession(false)}
            >
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </>
    );
  }
  if (authError) return <Failure message={authError} retry={refreshIdentity} />;
  if (identity === undefined)
    return (
      <div className="boot">
        <span className="wordmark">101</span>
        <p role="status">Abriendo tu espacio…</p>
      </div>
    );
  if (!identity)
    return (
      <Login
        onLogin={(id) => {
          ++authGeneration.current;
          setIdentity(id);
        }}
      />
    );
  if (screen === "login")
    return (
      <WorkspaceEntry
        target={params.get("next") || "/workspace/home"}
        businesses={identity.businesses}
        onSignOut={() => endSession(false)}
      />
    );
  if (!business && screen !== "onboarding")
    return (
      <div className="state">
        <h1>
          {requested ? "Este negocio no está disponible" : "Elige tu negocio"}
        </h1>
        <p>Elige uno de tus negocios para continuar.</p>
        {identity.businesses.map((b) => (
          <button
            className="button secondary"
            key={b.business_id}
            onClick={() =>
              navigate({
                business: b.business_id,
                customer: null,
                order: null,
                campaign: null,
                q: null,
                offset: null,
              })
            }
          >
            {b.name}
          </button>
        ))}
        <button className="button secondary" onClick={() => endSession(false)}>
          Cambiar de usuario
        </button>
      </div>
    );
  return (
    <div className={`workspace ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}>
      <aside
        className="sidebar"
        id="workspace-sidebar"
        hidden={sidebarCollapsed}
      >
        {nav()}
      </aside>
      <main
        className={`main ${selected && screen === "customers" ? "has-detail" : ""}`}
      >
        <header className="topbar">
          {sidebarCollapsed && (
            <button
              ref={sidebarOpen}
              type="button"
              className="icon-button sidebar-reopen"
              aria-label="Mostrar barra lateral"
              title="Mostrar barra lateral"
              aria-controls="workspace-sidebar"
              aria-expanded={false}
              onClick={() => toggleSidebar(false)}
            >
              <PanelLeftOpen size={20} />
            </button>
          )}
          <button
            className="icon-button mobile-menu"
            aria-label="Abrir navegación"
            onClick={() => setMenu(true)}
          >
            <Menu />
          </button>
          <div className="breadcrumb">
            {screen === "social" ? (
              <Palette size={16} />
            ) : screen === "home" ? (
              <House size={16} />
            ) : screen === "sales" ? (
              <ShoppingBag size={16} />
            ) : screen === "campaigns" ? (
              <Megaphone size={16} />
            ) : screen === "analytics" ? (
              <ChartNoAxesColumnIncreasing size={16} />
            ) : screen === "onboarding" ? (
              <LayersIcon size={16} />
            ) : screen === "settings" ? (
              <SlidersHorizontal size={16} />
            ) : screen === "identity" ? (
              <Palette size={16} />
            ) : (
              <Users size={16} />
            )}
            <span>{screenNames[screen]}</span>
          </div>
          <div className="topbar-right">
            {policy?.demo_mode && (
              <span className="demo-badge">
                <span />
                Demostración · datos ficticios
              </span>
            )}
          </div>
        </header>
        {policy?.internal_tools && <ColorPreview />}
        {screen === "customers" && (
          <CustomerSections
            business={bid}
            params={params}
            navigate={navigate}
          />
        )}
        {["sales", "customers"].includes(screen) && params.get("date_from") && (
          <div className="date-context">
            {params.get("date_from")} — {params.get("date_to")} ·{" "}
            {screen === "sales" && params.get("view") === "reservations"
              ? "por fecha de reserva"
              : "por fecha de creación"}{" "}
            <button
              className="back-link"
              onClick={() =>
                navigate({ date_from: null, date_to: null, offset: null })
              }
            >
              Ver todas las fechas
            </button>
          </div>
        )}
        {screen === "onboarding" || (!business && identity.platform_admin) ? (
          identity.platform_admin ? (
            <OnboardingView
              key={identity.actor_id}
              csrf={identity.csrf}
              actor={identity.actor_id}
              params={params}
              navigate={navigate}
            />
          ) : (
            <div className="state">
              <h1>Acceso restringido</h1>
              <p>Solo un administrador de 101 puede gestionar negocios.</p>
            </div>
          )
        ) : screen === "social" ? (
          <SocialWorkspace
            key={bid}
            business={bid}
            csrf={identity.csrf}
            demo={!!policy?.demo_mode}
          />
        ) : screen === "reports" ? (
          <ReportsWorkspace
            key={bid}
            business={bid}
            csrf={identity.csrf}
            params={params}
            navigate={navigate}
          />
        ) : screen === "connections" ? (
          <ChannelConnections
            key={bid + params.get("provider")}
            business={bid}
            params={params}
            navigate={navigate}
            csrf={identity.csrf}
            permissions={business?.permissions || []}
            demo={!!policy?.demo_mode}
          />
        ) : screen === "website" ? (
          <CheckoutDesignView key={bid} business={bid} csrf={identity.csrf} permissions={business?.permissions || []} />
        ) : screen === "settings" ? (
          <OperationSettingsView
            key={bid}
            business={bid}
            csrf={identity.csrf}
            permissions={business?.permissions || []}
            params={params}
            navigate={navigate}
          />
        ) : screen === "home" ? (
          <HomeView business={bid} params={params} navigate={navigate} />
        ) : screen === "analytics" ? (
          <AnalyticsView business={bid} params={params} navigate={navigate} />
        ) : screen === "identity" ? (
          policy?.internal_tools ? (
            <IdentityView />
          ) : null
        ) : screen === "campaigns" ? (
          <CampaignWorkspace
            key={bid}
            business={bid}
            params={params}
            navigate={navigate}
            csrf={identity.csrf}
            permissions={business?.permissions || []}
            demo={!!policy?.demo_mode}
          />
        ) : screen === "sales" ? (
          <SalesWorkspace
            key={bid}
            rememberScroll={(value) => {
              routeScroll.current[bid + "sales"] = value;
            }}
            initialScroll={routeScroll.current[bid + "sales"] || 0}
            business={bid}
            permissions={business?.permissions || []}
            csrf={identity.csrf}
            params={params}
            navigate={navigate}
          />
        ) : screen === "customers" && params.get("view") === "signup" ? (
          <SignupTools key={bid} business={bid} />
        ) : catalogue ? (
          <Catalog
            key={bid + params.get("view")}
            business={bid}
            params={params}
            navigate={navigate}
          />
        ) : loyalty ? (
          <LoyaltyWorkspace
            key={bid}
            business={bid}
            permissions={business?.permissions || []}
            csrf={identity.csrf}
            params={params}
            navigate={navigate}
          />
        ) : (
          <div className="page">
            <section className="page-heading">
              <div>
                <span className="eyebrow">CONOCE A QUIENES VUELVEN</span>
                <h1>Clientes</h1>
              </div>
              <div className="loyalty-directory-actions">
                <div className="loyalty-entry">
                  <a
                    className="button secondary"
                    href={`?business=${encodeURIComponent(bid)}&view=loyalty`}
                    onClick={(e) => {
                      if (
                        !e.metaKey &&
                        !e.ctrlKey &&
                        !e.shiftKey &&
                        !e.altKey
                      ) {
                        e.preventDefault();
                        navigate(
                          { view: "loyalty", customer: null, loyaltyId: null },
                          true,
                        );
                      }
                    }}
                  >
                    Fidelización <ArrowRight size={15} />
                  </a>
                </div>
                <button className="button primary" onClick={() => setQr(true)}>
                  <QrCode size={17} />
                  Invitar clientes
                  <ArrowRight size={16} />
                </button>
              </div>
            </section>
            <div className="overview">
              <div className="overview-stat">
                <span>Clientes en tu negocio</span>
                <strong>
                  {list.data ? count(list.data.total) : "—"}
                  <Users size={21} />
                </strong>
                <small>Total histórico de contactos</small>
              </div>
              <div className="overview-stat">
                <span>Registros verificados</span>
                <strong>
                  {list.data?.registered != null
                    ? count(list.data.registered)
                    : "—"}
                  <Check size={21} />
                </strong>
                <small>Total histórico · teléfono o correo</small>
              </div>
              <button className="invite-tile" onClick={() => setQr(true)}>
                <span className="tile-qr">
                  <QrCode size={34} strokeWidth={1.6} />
                </span>
                <span>
                  <strong>
                    Compartir QR <ArrowUp />
                  </strong>
                </span>
              </button>
            </div>
            <section
              className="customer-surface"
              aria-label="Directorio de clientes"
            >
              <div className="surface-heading">
                <h2>
                  Directorio{" "}
                  <span>{list.data ? count(list.data.count) : "…"}</span>
                </h2>
                <span className="quiet">
                  Ordenado por registro más reciente
                </span>
              </div>
              <div className="toolbar">
                <div className="tabs" aria-label="Filtrar clientes">
                  {[
                    ["all", "Todos"],
                    ["registered", "Registrados"],
                  ].map(([value, text]) => (
                    <button
                      key={value}
                      className={kind === value ? "selected" : ""}
                      aria-pressed={kind === value}
                      onClick={() =>
                        navigate({
                          kind: value === "all" ? null : value,
                          offset: null,
                          customer: null,
                        })
                      }
                    >
                      {text}
                    </button>
                  ))}
                </div>
                <div className="search-controls">
                  <label className="search">
                    <Search size={17} />
                    <input
                      type="search"
                      placeholder="Buscar nombre, correo o teléfono"
                      aria-label="Buscar clientes"
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                    />
                    {search && (
                      <button
                        aria-label="Limpiar búsqueda"
                        onClick={() => {
                          setSearch("");
                          navigate({ q: null, offset: null });
                        }}
                      >
                        <X size={15} />
                      </button>
                    )}
                  </label>
                  <label className="filter">
                    <SlidersHorizontal size={16} />
                    <span className="sr-only">Filtrar por contacto</span>
                    <select
                      aria-label="Filtrar por contacto"
                      value={["phone", "email"].includes(kind) ? kind : "all"}
                      onChange={(e) =>
                        navigate({
                          kind:
                            e.target.value === "all" ? null : e.target.value,
                          offset: null,
                          customer: null,
                        })
                      }
                    >
                      <option value="all">Contacto</option>
                      <option value="email">Con correo</option>
                      <option value="phone">Con teléfono</option>
                    </select>
                  </label>
                </div>
              </div>
              <div
                className="list-scroll"
                ref={listRef}
                data-testid="customer-list"
              >
                {list.error ? (
                  <Failure message={list.error} retry={list.retry} />
                ) : !list.data ? (
                  <Loading />
                ) : list.data.count === 0 ? (
                  <div className="state">
                    <div className="empty-icon">
                      <Users size={26} />
                    </div>
                    <h3>
                      {query
                        ? "Nadie por aquí con ese nombre"
                        : "Todo empieza con el primer cliente"}
                    </h3>
                    <p>
                      {query
                        ? "Prueba con otro nombre, correo o teléfono."
                        : "Comparte tu enlace o QR para invitar a tu gente."}
                    </p>
                    <button
                      className="button secondary"
                      onClick={() => {
                        if (query) {
                          setSearch("");
                          navigate({ q: null, offset: null });
                        } else if (kind !== "all") {
                          navigate({ kind: null, offset: null });
                        } else setQr(true);
                      }}
                    >
                      {query
                        ? "Limpiar búsqueda"
                        : kind !== "all"
                          ? "Ver todos"
                          : "Compartir QR"}
                    </button>
                  </div>
                ) : (
                  <table>
                    <thead>
                      <tr>
                        <th>Cliente</th>
                        <th>Contacto</th>
                        <th>Registro</th>
                        <th>Desde</th>
                        <th>
                          <span className="sr-only">Abrir</span>
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {list.data.items.map((c) => (
                        <tr
                          key={c.id}
                          className={selected === c.id ? "current" : ""}
                        >
                          <td>
                            <a
                              className="customer-link"
                              href={`?${new URLSearchParams({ ...Object.fromEntries(params), business: bid, customer: c.id })}`}
                              onClick={(e) => selectCustomer(e, c.id)}
                            >
                              <Avatar customer={c} />
                              <span>
                                <strong>{label(c)}</strong>
                                <small>
                                  {c.name
                                    ? c.email ||
                                      c.phone ||
                                      "Sin datos de contacto"
                                    : "Nombre pendiente"}
                                </small>
                              </span>
                            </a>
                          </td>
                          <td>
                            <div className="contact-cell">
                              <span>{c.email || "Sin correo"}</span>
                              <small>{c.phone || "Sin teléfono"}</small>
                            </div>
                          </td>
                          <td>
                            <span
                              className={`badge ${c.registered ? "verified" : ""}`}
                            >
                              {c.registered ? (
                                <>
                                  <Check size={12} />
                                  Verificado
                                </>
                              ) : (
                                "Sin registro"
                              )}
                            </span>
                          </td>
                          <td className="date-cell">{date(c.created_at)}</td>
                          <td>
                            <ChevronRight size={16} className="row-chevron" />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
              <footer className="table-footer">
                <span aria-live="polite">
                  {list.data
                    ? `${list.data.count ? offset + 1 : 0}–${Math.min(offset + 25, list.data.count)} de ${count(list.data.count)} clientes`
                    : "Cargando…"}
                </span>
                <div>
                  <button
                    className="icon-button"
                    aria-label="Página anterior"
                    disabled={!offset || !list.data}
                    onClick={() =>
                      navigate({
                        offset: String(Math.max(0, offset - 25)),
                        customer: null,
                      })
                    }
                  >
                    <ChevronLeft size={17} />
                  </button>
                  <span>Página {Math.floor(offset / 25) + 1}</span>
                  <button
                    className="icon-button"
                    aria-label="Página siguiente"
                    disabled={!list.data || offset + 25 >= list.data.count}
                    onClick={() =>
                      navigate({ offset: String(offset + 25), customer: null })
                    }
                  >
                    <ChevronRight size={17} />
                  </button>
                </div>
              </footer>
            </section>
            <footer className="page-footer">
              <span>Las relaciones se construyen, visita a visita.</span>
              <span className="footer-mark">101</span>
            </footer>
          </div>
        )}
        {selected && screen === "customers" && (
          <CustomerDetail
            key={`${bid}:${selected}`}
            business={bid}
            id={selected}
            close={closeDetail}
          />
        )}
      </main>
      <Dialog.Root open={menu} onOpenChange={setMenu}>
        <Dialog.Portal>
          <Dialog.Backdrop className="backdrop" />
          <Dialog.Popup className="mobile-nav">
            <Dialog.Title className="sr-only">Navegación</Dialog.Title>
            <Dialog.Close
              className="icon-button close-nav"
              aria-label="Cerrar navegación"
            >
              <PanelLeftClose size={20} />
            </Dialog.Close>
            {nav(true)}
          </Dialog.Popup>
        </Dialog.Portal>
      </Dialog.Root>
      <SignupDialog business={bid} open={qr} setOpen={setQr} />
    </div>
  );
}
function ArrowUp() {
  return <ArrowRight size={14} className="diagonal" />;
}
function CustomerDetail({
  business,
  id,
  close,
}: {
  business: string;
  id: string;
  close: () => void;
}) {
  const result = useResource<Detail>(
    `${endpoint(business)}/customers/${encodeURIComponent(id)}`,
  );
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    heading.current?.focus();
  }, [result.data]);
  const d = result.data;
  return (
    <aside className="detail" aria-label="Detalle del cliente">
      <div className="detail-top">
        <button className="back-link" onClick={close}>
          <ArrowLeft size={16} />
          Directorio
        </button>
        <button
          className="icon-button"
          aria-label="Cerrar detalle"
          onClick={close}
        >
          <X size={19} />
        </button>
      </div>
      {result.error ? (
        <Failure message={result.error} retry={result.retry} />
      ) : !d ? (
        <Loading />
      ) : (
        <div className="detail-body">
          <Avatar customer={d} large />
          <span className="eyebrow">
            CLIENTE DESDE {date(d.created_at).toUpperCase()}
          </span>
          <h2 ref={heading} tabIndex={-1}>
            {label(d)}
          </h2>
          <span className={`badge ${d.membership ? "verified" : ""}`}>
            {d.membership ? (
              <>
                <Check size={12} />
                Registro verificado
              </>
            ) : (
              "Contacto sin registro"
            )}
          </span>
          <div className="contact-details">
            <div>
              <Mail size={16} />
              <span>{d.email || "Correo no registrado"}</span>
            </div>
            <div>
              <Phone size={16} />
              <span>{d.phone || "Teléfono no registrado"}</span>
            </div>
          </div>
          {d.membership && (
            <div className="membership-note">
              <QrCode size={17} />
              <span>
                Se unió por {source(d.membership.source).toLowerCase()}
                <small>
                  {date(d.membership.created_at)}
                  {d.membership.scope === "test" ? " · Prueba" : ""}
                </small>
              </span>
            </div>
          )}
          <section className="detail-section">
            <div className="section-title">
              <h3>Compras asociadas</h3>
              <ShoppingBag size={17} />
            </div>
            {d.money.length ? (
              d.money.map((m) => (
                <div className="money" key={m.scope + m.currency}>
                  <span className="eyebrow">
                    {m.scope === "test" ? "SIMULACIÓN" : "PAGOS DEL PROVEEDOR"}{" "}
                    · {m.currency}
                  </span>
                  <strong>{amount(m.net_minor, m.currency)}</strong>
                  <span>Capturado menos devoluciones</span>
                  <dl>
                    <div>
                      <dt>Pedidos con pago confirmado</dt>
                      <dd>{m.paid_orders}</dd>
                    </div>
                    <div>
                      <dt>Capturado</dt>
                      <dd>{amount(m.captured_minor, m.currency)}</dd>
                    </div>
                    <div>
                      <dt>Devuelto</dt>
                      <dd>{amount(m.refunded_minor, m.currency)}</dd>
                    </div>
                  </dl>
                </div>
              ))
            ) : (
              <p className="muted">Todavía no hay pagos confirmados.</p>
            )}
            <p className="detail-note">
              La coincidencia de un teléfono en un pedido no confirma la
              identidad de quien compró.
            </p>
          </section>
          <section className="detail-section">
            <div className="section-title">
              <h3>Permisos de contacto</h3>
              <MessageCircle size={17} />
            </div>
            <p className="detail-note">
              Registrarse no autoriza mensajes promocionales.
            </p>
            {d.permissions.length ? (
              d.permissions.map((p) => (
                <div className="permission" key={p.channel + p.scope}>
                  <div>
                    <strong>
                      {{ email: "Correo", sms: "SMS", whatsapp: "WhatsApp" }[
                        p.channel
                      ] || p.channel}
                    </strong>
                    <small>
                      {p.scope === "test"
                        ? "Prueba"
                        : p.scope === "live"
                          ? "En vivo"
                          : "Prueba de proveedor"}{" "}
                      · {date(p.at)}
                    </small>
                  </div>
                  <span
                    className={`badge ${p.state === "granted" ? "verified" : p.state === "unknown" ? "" : "withdrawn"}`}
                  >
                    {{
                      granted: "Con permiso",
                      withdrawn: "Retirado",
                      suppressed: "Suprimido",
                      unknown: "Sin evidencia",
                    }[p.state] || "Sin evidencia"}
                  </span>
                </div>
              ))
            ) : (
              <p className="muted">
                {d.permission_available
                  ? "No hay permisos registrados."
                  : "Los permisos aún no están disponibles."}
              </p>
            )}
            <p className="detail-note">
              Cada campaña vuelve a comprobar permiso, restricciones y
              disponibilidad antes de enviar.
            </p>
          </section>
          <section className="detail-section">
            <div className="section-title">
              <h3>Pedidos recientes</h3>
              <span>{d.order_count}</span>
            </div>
            {!d.orders.length ? (
              <p className="muted">Aún no hay pedidos asociados.</p>
            ) : (
              <>
                <p className="detail-note">Hasta 20 pedidos más recientes.</p>
                {d.orders.map((o) => (
                  <div className="order" key={o.id}>
                    <div>
                      <strong>#{o.code}</strong>
                      <small>
                        {date(o.created_at)} ·{" "}
                        {o.identity_verified
                          ? "Identidad verificada"
                          : "Compra como invitado"}
                      </small>
                    </div>
                    <div>
                      <strong>{amount(o.total_minor, o.currency)}</strong>
                      <small>
                        {{
                          paid: "Pagado",
                          refunded: "Devuelto",
                          pending: "Pendiente",
                          unpaid: "Sin pagar",
                          failed: "Fallido",
                        }[o.payment_status] || o.payment_status}
                      </small>
                    </div>
                  </div>
                ))}
              </>
            )}
          </section>
        </div>
      )}
    </aside>
  );
}
function SignupDialog({
  business,
  open,
  setOpen,
}: {
  business: string;
  open: boolean;
  setOpen: (v: boolean) => void;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Portal>
        <Dialog.Backdrop className="backdrop" />
        <Dialog.Popup className="qr-dialog">
          <Dialog.Close
            className="icon-button dialog-close"
            aria-label="Cerrar invitación"
          >
            <X size={20} />
          </Dialog.Close>
          <span className="eyebrow">DE TU MOSTRADOR A SU TELÉFONO</span>
          <Dialog.Title>Haz crecer tu gente.</Dialog.Title>
          <Dialog.Description>
            Un código QR para tu negocio. Compártelo, imprímelo o déjalo donde
            empieza una conversación.
          </Dialog.Description>
          {open && <SignupContent key={business} business={business} />}
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
restoreLegacySection();
createRoot(document.getElementById("root")!).render(
  <CSPProvider disableStyleElements>
    {location.pathname === "/connections/instagram/callback" ? (
      <InstagramCallback />
    ) : (
      <App />
    )}
  </CSPProvider>,
);
