import React, { useEffect, useRef, useState } from "react";
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
  Mail,
  Megaphone,
  Menu,
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
import { LoyaltyWorkspace } from "./loyalty";
import {
  HomeView,
  AnalyticsView,
  IdentityView,
  periodQuery,
} from "./workspace-views";
import { CampaignView } from "./campaign-workspace";
import { SocialWorkspace } from "./social";
import { ColorPreview } from "./color-preview";
const screenFromPath = () => {
  const path = location.pathname.split("/").pop() || "home";
  return ["sales", "customers", "campaigns", "analytics", "identity", "social"].includes(
    path,
  )
    ? path
    : "home";
};
const screenNames: Record<string, string> = {
  home: "Inicio",
  sales: "Ventas",
  customers: "Clientes",
  campaigns: "Campañas",
  social: "Contenido",
  analytics: "Analítica web",
  identity: "Identidad",
};

type Business = {
  business_id: string;
  name: string;
  slug: string;
  role: string;
  permissions: string[];
};
type Identity = { username: string; csrf: string; businesses: Business[] };
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
type Signup = {
  business_name: string;
  signup_url: string | null;
  qr_url: string | null;
  available: boolean;
  mode: string;
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
        <span className="eyebrow">TU NEGOCIO, A MANO</span>
        <h1>
          Un buen día
          <br />
          empieza aquí.
        </h1>
        <p>Entra a tu espacio de trabajo.</p>
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
      <small>101 · Herramientas para hacer más.</small>
    </div>
  );
}
function App() {
  const [identity, setIdentity] = useState<Identity | null | undefined>();
  const [authError, setAuthError] = useState("");
  const [params, setParams] = useState(
    () => new URLSearchParams(location.search),
  );
  const [screen, setScreen] = useState(screenFromPath());
  const routeMemory = useRef<Record<string, string>>({});
  const routeScroll = useRef<Record<string, number>>({});
  const [menu, setMenu] = useState(false);
  const [qr, setQr] = useState(
    new URLSearchParams(location.search).get("invite") === "1",
  );
  const [policy, setPolicy] = useState<{ demo_mode: boolean }>();
  const [search, setSearch] = useState(params.get("q") || "");
  const scrollRef = useRef(0);
  const returnFocus = useRef<HTMLAnchorElement | null>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const previousCustomer = useRef(params.get("customer"));
  const refreshIdentity = () => {
    setAuthError("");
    api<Identity>("/api/staff/me")
      .then(setIdentity)
      .catch((e) => {
        if (e.status === 401) setIdentity(null);
        else setAuthError(e.message);
      });
  };
  useEffect(() => {
    refreshIdentity();
    api<{ demo_mode: boolean }>("/api/browser-policy")
      .then(setPolicy)
      .catch(() => {});
    const pop = () => {
      setScreen(screenFromPath());
      setParams(new URLSearchParams(location.search));
      setSearch(new URLSearchParams(location.search).get("q") || "");
    };
    const expire = () => setIdentity(null);
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
    return () => {
      document.removeEventListener("visibilitychange", visible);
      window.removeEventListener("pageshow", restored);
      window.removeEventListener("popstate", pop);
      window.removeEventListener("session-expired", expire);
    };
  }, []);
  const requested = params.get("business");
  const business =
    identity?.businesses.find((b) => b.business_id === requested) ||
    (!requested ? identity?.businesses[0] : undefined);
  const bid = business?.business_id || "";
  const loyalty = screen === "customers" && params.get("view") === "loyalty";
  const selected = loyalty ? null : params.get("customer");
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
    if (screen !== "customers" || loyalty || search === query) return;
    const timer = setTimeout(
      () => navigate({ q: search.trim(), offset: null, customer: null }),
      180,
    );
    return () => clearTimeout(timer);
  }, [search, query, screen, loyalty]);
  const list = useResource<Listing>(
    bid && screen === "customers" && !loyalty
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
  const legacy = (path: string) =>
    `${path}?business_id=${encodeURIComponent(bid)}`;
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
  function nav() {
    return (
      <>
        <div className="brand">
          <a
            href="/workspace/home"
            aria-label="101 Inicio"
            className="wordmark"
          >
            101<span>workspace</span>
          </a>
        </div>
        <div className="business">
          <span className="business-icon">
            <ShoppingBag size={20} />
          </span>
          <div>
            {identity && identity.businesses.length > 1 ? (
              <>
                <label className="sr-only" htmlFor="business">
                  Negocio
                </label>
                <select
                  id="business"
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
              <strong>{business?.name || "Selecciona un negocio"}</strong>
            )}
            <span>Espacio del negocio</span>
          </div>
        </div>
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
          <a href={`/workspace/social?business=${bid}`} onClick={(e) => goScreen(e, "social")} className={screen === "social" ? "active" : ""}><Palette size={18} />Contenido</a>
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
          <details className="presence">
            <summary>
              <Globe2 />
              Presencia
              <ChevronDown size={14} />
            </summary>
            <div>
              <a href={`/r/${encodeURIComponent(business?.slug || bid)}`}>
                Sitio web
                <ExternalLink size={13} />
              </a>
              <a href={legacy("/connections")}>Google</a>
              <span title="La conexión social todavía no está disponible">
                Social <small>Próximamente</small>
              </span>
            </div>
          </details>
        </nav>
        <div className="nav-bottom">
          <a
            href={`/workspace/identity?business=${bid}`}
            onClick={(e) => goScreen(e, "identity")}
          >
            <Palette />
            Identidad
          </a>
          <a href={legacy("/connections")}>
            <Plug />
            Conexiones
            <ExternalLink className="nav-external" />
          </a>
          <div className="account">
            <span className="account-avatar">
              {identity?.username.slice(0, 1).toUpperCase()}
            </span>
            <span>
              <strong>{identity?.username}</strong>
              <small>
                {business?.role === "manager" ? "Administrador" : "Equipo"}
              </small>
            </span>
            <button
              className="icon-button"
              aria-label="Cerrar sesión"
              onClick={async () => {
                try {
                  await api("/api/staff/logout", {
                    method: "POST",
                    headers: { "X-101-CSRF": identity?.csrf || "" },
                  });
                  setIdentity(null);
                } catch {
                  setAuthError(
                    "No se pudo cerrar la sesión. Inténtalo de nuevo.",
                  );
                }
              }}
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
          setIdentity(id);
          navigate({ customer: null });
        }}
      />
    );
  if (!business)
    return (
      <div className="state">
        <h1>Este negocio no está disponible</h1>
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
      </div>
    );
  return (
    <div className="workspace">
      <aside className="sidebar">{nav()}</aside>
      <main
        className={`main ${selected && screen === "customers" ? "has-detail" : ""}`}
      >
        <header className="topbar">
          <button
            className="icon-button mobile-menu"
            aria-label="Abrir navegación"
            onClick={() => setMenu(true)}
          >
            <Menu />
          </button>
          <div className="breadcrumb">
            {screen === "social" ? <Palette size={16} /> : screen === "home" ? (
              <House size={16} />
            ) : screen === "sales" ? (
              <ShoppingBag size={16} />
            ) : screen === "campaigns" ? (
              <Megaphone size={16} />
            ) : screen === "analytics" ? (
              <ChartNoAxesColumnIncreasing size={16} />
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
            <span className="version-label">HECHO PARA TU DÍA A DÍA</span>
          </div>
        </header>
        {policy?.demo_mode && <ColorPreview />}
        {["sales", "customers"].includes(screen) && params.get("date_from") && (
          <div className="date-context">
            {params.get("date_from")} — {params.get("date_to")} · por fecha de
            creación{" "}
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
        {screen === "social" ? (<SocialWorkspace key={bid} business={bid} csrf={identity.csrf} demo={!!policy?.demo_mode} />) : screen === "home" ? (
          <HomeView business={bid} params={params} navigate={navigate} />
        ) : screen === "analytics" ? (
          <AnalyticsView business={bid} params={params} navigate={navigate} />
        ) : screen === "identity" ? (
          <IdentityView />
        ) : screen === "campaigns" ? (
          <CampaignView
            key={bid}
            business={bid}
            params={params}
            navigate={navigate}
            csrf={identity.csrf}
            permissions={business.permissions}
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
            permissions={business.permissions}
            csrf={identity.csrf}
            params={params}
            navigate={navigate}
          />
        ) : loyalty ? (
          <LoyaltyWorkspace
            key={bid}
            business={bid}
            permissions={business.permissions}
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
                <p>Cada visita empieza con una persona.</p>
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
                    Un escaneo.
                    <br />
                    Una nueva conexión.
                  </strong>
                  <small>
                    Comparte tu código QR <ArrowUp />
                  </small>
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
              <X />
            </Dialog.Close>
            {nav()}
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
  const result = useResource<Signup>(
    open ? `${endpoint(business)}/signup` : null,
  );
  const [copied, setCopied] = useState(false);
  useEffect(() => setCopied(false), [open, business]);
  const d = result.data;
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
          {result.error ? (
            <Failure message={result.error} retry={result.retry} />
          ) : !d ? (
            <Loading />
          ) : d.signup_url ? (
            <>
              <div className="qr-card">
                <span className="qr-business">{d.business_name}</span>
                <img
                  src={`${endpoint(business)}/signup/qr.png`}
                  width="208"
                  height="208"
                  alt={`Código QR de registro para ${d.business_name}`}
                />
                <strong>Escanea. Únete. Vuelve.</strong>
                <span>Con tu teléfono o tu correo.</span>
              </div>
              {d.mode === "test" && (
                <p className="test-note">
                  Demostración local · registro y códigos de prueba.
                </p>
              )}
              {!d.available && (
                <p role="status" className="test-note">
                  La verificación aún no está configurada. El enlace estará
                  disponible cuando se active.
                </p>
              )}
              <div className="qr-downloads">
                <a
                  className="button primary"
                  download
                  href={`${endpoint(business)}/signup/qr.png`}
                >
                  <ArrowDownToLine size={16} />
                  Descargar PNG
                </a>
                <a
                  className="button secondary"
                  download
                  href={`${endpoint(business)}/signup/qr.svg`}
                >
                  SVG
                  <ArrowDownToLine size={15} />
                </a>
              </div>
              <label className="link-label">
                O comparte el enlace
                <input
                  readOnly
                  value={d.signup_url}
                  aria-label="Enlace de registro"
                  onFocus={(e) => e.target.select()}
                />
              </label>
              <button
                className="button copy-button"
                onClick={async () => {
                  try {
                    await navigator.clipboard.writeText(d.signup_url!);
                    setCopied(true);
                  } catch {
                    setCopied(false);
                  }
                }}
              >
                {copied ? <Check size={16} /> : <Copy size={16} />}
                <span aria-live="polite">
                  {copied ? "Enlace copiado" : "Copiar enlace"}
                </span>
              </button>
            </>
          ) : (
            <div className="state">
              <QrCode />
              <h3>Tu enlace aún no está listo</h3>
              <p>Falta configurar la dirección pública del negocio.</p>
              <a href="/customers/signup" className="button secondary">
                Ver configuración
              </a>
            </div>
          )}
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
createRoot(document.getElementById("root")!).render(
  <CSPProvider disableStyleElements>
    <App />
  </CSPProvider>,
);
