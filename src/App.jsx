import { useEffect, useMemo, useRef, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { api } from "./api.js";
import AdminChat from "./AdminChat.jsx";

const menuCategories = ["Starters", "Main course", "Breads", "Drinks", "Desserts", "Breakfast", "Thalis"];
const categoriesByMeal = {
  breakfast: ["All items"],
  lunch: ["All items", "Starters", "Main course", "Breads", "Drinks", "Desserts", "Thalis"],
  dinner: ["All items", "Starters", "Main course", "Breads", "Drinks", "Desserts", "Thalis"],
};
const mealServices = [
  { id: "breakfast", name: "Breakfast", time: "7:00 AM – 11:00 AM" },
  { id: "lunch", name: "Lunch", time: "11:00 AM – 4:00 PM" },
  { id: "dinner", name: "Dinner", time: "6:00 PM – 11:00 PM" },
];
const imageUrl = (image) => image.startsWith("http")
  ? image
  : `https://images.unsplash.com/${image}?auto=format&fit=crop&w=640&q=80`;
const money = (amount) => `₹${Number(amount || 0).toLocaleString("en-IN")}`;
const localDateValue = (date = new Date()) => {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
};

function Icon({ name, size = 18 }) {
  const paths = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" /><rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" /></>,
    menu: <><path d="M4 6h16M4 12h16M4 18h16" /></>,
    receipt: <><path d="M5 3h14v18l-3-2-4 2-4-2-3 2z" /><path d="M9 8h6M9 12h6" /></>,
    settings: <><circle cx="12" cy="12" r="3" /><path d="m19.4 15 .1.1 1.4 1.1-1.4 2.4-1.7-.7a8 8 0 0 1-1.5.9l-.3 1.8h-2.8l-.3-1.8a8 8 0 0 1-1.5-.9l-1.7.7-1.4-2.4 1.4-1.1a7 7 0 0 1 0-1.8l-1.4-1.1 1.4-2.4 1.7.7a8 8 0 0 1 1.5-.9l.3-1.8h2.8l.3 1.8a8 8 0 0 1 1.5.9l1.7-.7 1.4 2.4-1.4 1.1a7 7 0 0 1-.1 1.7z" transform="translate(-1 -1) scale(1.08)" /></>,
    search: <><circle cx="10.8" cy="10.8" r="6.8" /><path d="m16 16 4 4" /></>,
    plus: <><path d="M12 5v14M5 12h14" /></>,
    minus: <path d="M5 12h14" />,
    close: <><path d="m6 6 12 12M18 6 6 18" /></>,
    arrow: <><path d="M5 12h14M13 6l6 6-6 6" /></>,
    clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
    check: <path d="m5 12 4 4L19 6" />,
    chevron: <path d="m8 10 4 4 4-4" />,
    users: <><circle cx="9" cy="8" r="3" /><path d="M3 20v-1a6 6 0 0 1 12 0v1M16 5.2a3 3 0 0 1 0 5.6M18 14a5 5 0 0 1 3 4.5V20" /></>,
    logout: <><path d="M10 17l5-5-5-5M15 12H3" /><path d="M12 3h7a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-7" /></>,
    edit: <><path d="m15 5 4 4M4 20l4-.8L19 8a2.1 2.1 0 0 0-3-3L5 16z" /></>,
    trash: <><path d="M4 7h16M10 11v6M14 11v6M5 7l1 14h12l1-14M9 7V4h6v3" /></>,
    receiptSmall: <><path d="M6 3h12v18l-3-2-3 2-3-2-3 2z" /></>,
    leaf: <><path d="M20 4c-9 0-15 4-15 11a5 5 0 0 0 5 5c7 0 11-6 10-16zM5 19c2-4 5-7 10-10" /></>,
    sparkle: <><path d="m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3zM19 15l.9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9L19 15z" /></>,
    calendar: <><rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" /></>,
    table: <><rect x="3" y="3" width="18" height="18" rx="2" /><path d="M3 9h18M3 15h18M9 9v12M15 9v12" /></>,
    inventory: <><path d="m7.5 4.27 9 5.15M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z" /><path d="m3.3 7 8.7 5 8.7-5M12 22V12" /></>,
    payment: <><rect x="2" y="5" width="20" height="14" rx="2" /><line x1="2" y1="10" x2="22" y2="10" /></>,
    refresh: <><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.19" /></>,
    trendingUp: <><polyline points="23 6 13.5 15.5 8.5 10.5 1 18" /><polyline points="17 6 23 6 23 12" /></>,
    info: <><circle cx="12" cy="12" r="10" /><line x1="12" y1="16" x2="12" y2="12" /><line x1="12" y1="8" x2="12.01" y2="8" /></>,
    filter: <><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" /></>,
    chevronUp: <path d="m16 14-4-4-4 4" />,
    chevronDown: <path d="m8 10 4 4 4-4" />,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name] || paths.sparkle}</svg>;
}

function LoginScreen({ onLogin, initialError = "" }) {
  const [selectedRole, setSelectedRole] = useState("staff");
  const [username, setUsername] = useState("staff@123");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(initialError);
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await api("/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password, role: selectedRole }),
      });
      window.localStorage.setItem("restaurant-token", result.token);
      onLogin(result.user);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-screen">
      <form className="login-card" onSubmit={submit}>
        <div className="brand-mark login-mark">S<span>.</span></div>
        <div className="eyebrow">SAFFRON & STONE · RESTAURANT</div>
        <h1>Welcome back.</h1>
        <p>Choose your account type, then sign in to continue.</p>
        <div className="login-role-picker" role="group" aria-label="Choose account type">
          <button type="button" className={selectedRole === "staff" ? "selected" : ""} aria-pressed={selectedRole === "staff"} onClick={() => { setSelectedRole("staff"); setUsername("staff@123"); setError(""); }}>
            <Icon name="users" size={17} /><span>Staff</span>
          </button>
          <button type="button" className={selectedRole === "admin" ? "selected" : ""} aria-pressed={selectedRole === "admin"} onClick={() => { setSelectedRole("admin"); setUsername("harsh@123"); setError(""); }}>
            <Icon name="settings" size={17} /><span>Admin</span>
          </button>
        </div>
        <label className="form-field">Username<input autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} required /></label>
        <label className="form-field">Password<input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
        {error && <div className="login-error" role="alert">{error}</div>}
        <button className="primary-button login-submit" disabled={busy}>{busy ? "Signing in..." : "Sign in"} <Icon name="arrow" size={16} /></button>
      </form>
    </div>
  );
}

function CustomerPortal() {
  const params = new URLSearchParams(window.location.search);
  const tableNumber = params.get("table") || "";
  const qrToken = params.get("token") || "";
  const [customerToken, setCustomerToken] = useState(() => window.localStorage.getItem("restaurant-customer-token") || "");
  const [customer, setCustomer] = useState(null);
  const [mode, setMode] = useState("login");
  const [menu, setMenu] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [orders, setOrders] = useState([]);
  const [cart, setCart] = useState([]);
  const [pointsToRedeem, setPointsToRedeem] = useState(0);
  const [preferences, setPreferences] = useState([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [chatQuestion, setChatQuestion] = useState("");
  const [chatAnswer, setChatAnswer] = useState("");
  const [cancelOrder, setCancelOrder] = useState(null);
  const [cancelReason, setCancelReason] = useState("");
  const subtotal = cart.reduce((sum, line) => sum + line.price * line.quantity, 0);
  const discount = Math.floor(pointsToRedeem / 10);
  const tax = Math.round((subtotal - discount) * 0.05);
  const total = subtotal - discount + tax;

  useEffect(() => {
    if (!customerToken) return;
    api("/customer/me", { token: customerToken })
      .then((profile) => {
        setCustomer(profile);
        setPreferences(profile.dietary_preferences || []);
      })
      .catch(() => {
        window.localStorage.removeItem("restaurant-customer-token");
        setCustomerToken("");
      });
  }, [customerToken]);

  useEffect(() => {
    if (!customerToken) return undefined;
    let active = true;
    const loadCustomerData = async () => {
      try {
        const [profile, items, suggestions, history] = await Promise.all([
          api("/customer/me", { token: customerToken }),
          api(`/public/menu?${preferences.map((diet) => `dietary=${encodeURIComponent(diet)}`).join("&")}`, { token: customerToken }),
          api("/customer/recommendations", { token: customerToken }),
          api("/customer/orders", { token: customerToken }),
        ]);
        if (active) {
          setCustomer(profile);
          setMenu(items);
          setRecommendations(suggestions.recommendations);
          setOrders(history);
        }
      } catch (requestError) {
        if (active) setError(requestError.message);
      }
    };
    loadCustomerData();
    const interval = window.setInterval(loadCustomerData, 7000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, [customerToken, preferences]);

  async function submitAuth(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError("");
    try {
      const payload = {
        username: String(form.get("username")).trim(),
        password: String(form.get("password")),
      };
      if (mode === "signup") {
        payload.display_name = String(form.get("display_name")).trim();
        payload.email = String(form.get("email")).trim() || null;
      }
      const result = await api(`/customer/${mode}`, { method: "POST", body: JSON.stringify(payload) });
      window.localStorage.setItem("restaurant-customer-token", result.token);
      setCustomerToken(result.token);
      setCustomer(result.user);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  async function savePreferences(nextPreferences) {
    try {
      await api("/customer/preferences", {
        token: customerToken,
        method: "PUT",
        body: JSON.stringify({ dietary_preferences: nextPreferences }),
      });
      setPreferences(nextPreferences);
      setNotice("Dietary preferences saved");
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  function addToCart(item) {
    setCart((current) => {
      const existing = current.find((line) => line.id === item.id);
      return existing
        ? current.map((line) => line.id === item.id ? { ...line, quantity: line.quantity + 1 } : line)
        : [...current, { ...item, quantity: 1 }];
    });
  }

  async function placeQrOrder() {
    if (!tableNumber || !qrToken || cart.length === 0) return;
    setBusy(true);
    setError("");
    try {
      const query = new URLSearchParams({ table: tableNumber, token: qrToken });
      const order = await api(`/customer/orders/qr?${query}`, {
        token: customerToken,
        method: "POST",
        body: JSON.stringify({
          items: cart.map((line) => ({ item_id: line.id, quantity: line.quantity })),
          note: "",
          points_to_redeem: Number(pointsToRedeem),
        }),
      });
      setCart([]);
      setPointsToRedeem(0);
      setNotice(`Order #${order.id} sent to the kitchen. Pay ${money(order.total)} at the counter.`);
      const history = await api("/customer/orders", { token: customerToken });
      setOrders(history);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  async function confirmOrderCancellation() {
    if (!cancelOrder) return;
    setBusy(true);
    setError("");
    try {
      await api(`/customer/orders/${cancelOrder.id}/cancel`, {
        token: customerToken,
        method: "POST",
        body: JSON.stringify({ reason: cancelReason.trim() || null }),
      });
      const [history, profile] = await Promise.all([
        api("/customer/orders", { token: customerToken }),
        api("/customer/me", { token: customerToken }),
      ]);
      setOrders(history);
      setCustomer(profile);
      setNotice(cancelOrder.payment_status === "paid"
        ? `Order #${cancelOrder.id} cancelled. Any payment refund must be handled separately by restaurant staff.`
        : `Order #${cancelOrder.id} cancelled.`);
      setCancelOrder(null);
      setCancelReason("");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  async function askChat(event) {
    event.preventDefault();
    setError("");
    try {
      const result = await api("/customer/chat", {
        token: customerToken,
        method: "POST",
        body: JSON.stringify({ question: chatQuestion }),
      });
      setChatAnswer(result.answer);
      setChatQuestion("");
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function signOutCustomer() {
    try {
      await api("/customer/logout", { token: customerToken, method: "POST" });
    } catch (requestError) {
      setError(`Could not revoke session: ${requestError.message}`);
    } finally {
      window.localStorage.removeItem("restaurant-customer-token");
      setCustomerToken("");
      setCustomer(null);
      setOrders([]);
      setCart([]);
    }
  }

  if (!customer) {
    return <div className="customer-page"><form className="customer-auth-card" onSubmit={submitAuth}>
      <div className="brand-mark">S<span>.</span></div><div className="eyebrow">SAFFRON & STONE · TABLE ORDERING</div>
      <h1>{mode === "signup" ? "Create your account" : "Welcome"}</h1>
      <p>{tableNumber ? `Ordering for ${tableNumber}. Sign in to continue.` : "Sign in to browse the menu and track your orders."}</p>
      {mode === "signup" && <label className="form-field">Your name<input name="display_name" required maxLength="120" /></label>}
      <label className="form-field">Username<input name="username" required minLength="3" autoComplete="username" /></label>
      {mode === "signup" && <label className="form-field">Email (optional)<input name="email" type="email" maxLength="254" /></label>}
      <label className="form-field">Password<input name="password" type="password" required minLength={mode === "signup" ? 8 : 1} autoComplete={mode === "signup" ? "new-password" : "current-password"} /></label>
      {error && <div className="login-error" role="alert">{error}</div>}
      <button className="primary-button login-submit" disabled={busy}>{busy ? "Please wait..." : mode === "signup" ? "Create account" : "Sign in"}</button>
      <button type="button" className="customer-mode-button" onClick={() => { setMode(mode === "login" ? "signup" : "login"); setError(""); }}>
        {mode === "signup" ? "Already registered? Sign in" : "New here? Create an account"}
      </button>
    </form></div>;
  }

  const dietOptions = ["vegetarian", "non-vegetarian", "vegan", "gluten-free", "dairy-free"];
  return <main className="customer-page">
    <header className="customer-header"><div className="brand"><div className="brand-mark">S<span>.</span></div><div><div className="brand-name">saffron<span>&</span>stone</div><div className="brand-caption">TABLE ORDERING</div></div></div>
      <div><strong>Welcome, {customer.display_name}</strong><span>{tableNumber || "Customer account"} · {customer.loyalty_points} loyalty points</span></div>
      <button className="logout-button" onClick={signOutCustomer}><Icon name="logout" size={16} /><span>Log out</span></button>
    </header>
    <div className="customer-content">
      {error && <div className="login-error" role="alert">{error}</div>}
      {notice && <div className="customer-notice">{notice}</div>}
      {!tableNumber || !qrToken ? <div className="profit-warning"><Icon name="sparkle" /><span>Use the QR code on your restaurant table to place an order. You can still browse recommendations and order history.</span></div> : null}
      <section className="customer-section">
        <div className="page-heading"><div><div className="eyebrow">PERSONALIZED MENU</div><h1>What sounds good?</h1><p>Dietary matches are shown only when menu information is verified by restaurant staff.</p></div></div>
        <div className="diet-filter"><strong>Filter menu</strong>{dietOptions.map((diet) => <label key={diet}><input type="checkbox" checked={preferences.includes(diet)} onChange={(event) => {
          const next = event.target.checked ? [...preferences, diet] : preferences.filter((entry) => entry !== diet);
          savePreferences(next);
        }} />{diet}</label>)}</div>
        {menu.length === 0 ? <div className="employee-empty">No items match these filters. Dietary results require verified menu information from restaurant staff.</div> : <div className="customer-menu-grid">{menu.map((item) => <article className="customer-menu-card" key={item.id}>
          <img src={imageUrl(item.image)} alt="" /><div><span className="eyebrow">{item.category}</span><h3>{item.name}</h3><p>{item.description}</p><strong>{money(item.price)}</strong>
            {item.dietary_verified && <small>{item.dietary_tags.join(" · ") || "Verified"}{item.allergens_text ? ` · Allergens: ${item.allergens_text}` : ""}</small>}
          </div><button className="primary-button" onClick={() => addToCart(item)}>Add</button>
        </article>)}</div>}
      </section>
      <section className="customer-section">
        <div className="table-title-row"><div><h2>Recommended for you</h2><span>Based on your orders and restaurant sales.</span></div></div>
        <div className="customer-recommendations">{recommendations.map((item) => <article key={item.id}><strong>{item.name}</strong><span>{item.reason}</span><button onClick={() => addToCart(item)}>Add · {money(item.price)}</button></article>)}</div>
      </section>
      <section className="customer-columns">
        <div className="customer-panel"><h2>Your cart {tableNumber && `· ${tableNumber}`}</h2>{cart.length === 0 ? <p>Your cart is empty.</p> : cart.map((line) => <div className="customer-cart-line" key={line.id}><span>{line.quantity} × {line.name}</span><strong>{money(line.quantity * line.price)}</strong><button onClick={() => setCart((current) => current.filter((entry) => entry.id !== line.id))}>Remove</button></div>)}
          <label className="form-field">Redeem loyalty points (10 points = ₹1)<input type="number" min="0" max={customer.loyalty_points} step="10" value={pointsToRedeem} onChange={(event) => setPointsToRedeem(Math.max(0, Math.floor(Number(event.target.value) / 10) * 10))} /></label>
          {discount > subtotal * 0.2 && <small className="login-error">Points can discount up to 20% of your food subtotal.</small>}
          <div className="customer-total"><span>Subtotal {discount ? `· ₹${discount} points discount` : ""} · tax included</span><strong>{money(total)}</strong></div>
          <button className="primary-button" disabled={busy || cart.length === 0 || !tableNumber || !qrToken || pointsToRedeem > customer.loyalty_points || discount > subtotal * 0.2} onClick={placeQrOrder}>Place order · pay at counter</button>
        </div>
        <div className="customer-panel"><h2>Ask the restaurant assistant</h2><p>Get menu information or check your latest order status.</p>
          <form className="customer-chat-form" onSubmit={askChat}><input value={chatQuestion} onChange={(event) => setChatQuestion(event.target.value)} placeholder="Ask about an item or order..." required maxLength={1000} /><button className="primary-button">Ask</button></form>
          {chatAnswer && <p className="customer-chat-answer">{chatAnswer}</p>}
        </div>
      </section>
      <section className="customer-section"><div className="table-title-row"><div><h2>Order history & kitchen progress</h2><span>Progress refreshes automatically. Unpaid orders are paid at the counter.</span></div></div>
        {orders.length === 0 ? <p>No orders yet.</p> : <div className="customer-orders">{orders.map((order) => {
          const completed = order.items.length > 0 && order.items.every((line) => line.prep_status === "delivered");
          return <article key={order.id} className={order.order_status === "cancelled" ? "customer-order-cancelled" : ""}>
            <div><strong>Order #{order.id} · {order.table_name} · {order.order_status === "cancelled" ? "Cancelled" : completed ? "Completed" : "In progress"}</strong><span>{order.items.map((line) => `${line.quantity} × ${line.name} (${line.prep_status})`).join(", ")}</span>{order.cancellation_reason && <small>Reason: {order.cancellation_reason}</small>}</div>
            <div><strong>{money(order.total)}</strong><span>{order.order_status === "cancelled" ? (order.payment_status === "paid" ? "Paid · refund handled separately" : "No payment due") : order.payment_status === "paid" ? "Paid" : "Pay at counter"}</span>{order.order_status === "active" && !completed && <button className="cancel-button customer-cancel-button" onClick={() => { setCancelOrder(order); setCancelReason(""); }}>Cancel order</button>}</div>
          </article>;
        })}</div>}
      </section>
      <section className="customer-section"><div className="table-title-row"><div><h2>Loyalty activity</h2><span>Earn 1 point per ₹100 after payment and delivery. Redeem 10 points for ₹1.</span></div></div>
        {(customer.loyalty_transactions || []).length === 0 ? <p>No points activity yet.</p> : <div className="customer-orders">{customer.loyalty_transactions.map((entry, index) => <article key={`${entry.reason}-${index}`}><div><strong>{entry.reason}</strong><span>{new Date(entry.created_at).toLocaleString()}</span></div><strong>{entry.points_delta > 0 ? "+" : ""}{entry.points_delta} points</strong></article>)}</div>}
      </section>
    </div>
    {cancelOrder && <div className="modal-backdrop" role="presentation"><section className="cancel-order-dialog" role="dialog" aria-modal="true" aria-labelledby="cancel-order-title">
      <button className="modal-close" aria-label="Close" onClick={() => setCancelOrder(null)}>×</button>
      <div className="eyebrow">ORDER CANCELLATION</div><h2 id="cancel-order-title">Cancel order #{cancelOrder.id}?</h2>
      <p>This cannot be undone. {cancelOrder.payment_status === "paid" ? "A payment refund is not issued automatically and must be handled by restaurant staff." : "Unused ingredients from queued items will be returned to inventory."}</p>
      <label className="form-field">Reason (optional)<textarea value={cancelReason} onChange={(event) => setCancelReason(event.target.value)} maxLength={500} placeholder="Tell us why you are cancelling" /></label>
      <div className="cancel-order-actions"><button className="secondary-button" disabled={busy} onClick={() => setCancelOrder(null)}>Keep order</button><button className="cancel-button" disabled={busy} onClick={confirmOrderCancellation}>{busy ? "Cancelling..." : "Confirm cancellation"}</button></div>
    </section></div>}
  </main>;
}

function ForecastChart({ history }) {
  const maximum = Math.max(1, ...history.map((point) => point.sales));
  const spacing = 600 / Math.max(1, history.length);
  const barWidth = Math.min(48, spacing * 0.62);
  return (
    <svg className="forecast-chart" viewBox="0 0 650 220" role="img" aria-label="Recent monthly sales and next month sales forecast">
      {[0, 1, 2, 3].map((line) => {
        const y = 170 - line * 42;
        return <line key={line} x1="30" x2="635" y1={y} y2={y} className="chart-grid-line" />;
      })}
      {history.map((point, index) => {
        const height = Math.max(point.sales > 0 ? 3 : 0, (point.sales / maximum) * 126);
        const x = 30 + index * spacing + (spacing - barWidth) / 2;
        const month = new Date(`${point.month}-01T00:00:00`).toLocaleDateString("en-IN", { month: "short" });
        const label = point.kind === "forecast" ? "Next month estimate" : point.kind === "current" ? "This month estimate" : "Past sales";
        return <g key={point.month}>
          <rect x={x} y={170 - height} width={barWidth} height={height} rx="4" className={`chart-bar ${point.kind}`}>
            <title>{`${month}: ${money(point.sales)} · ${label}`}</title>
          </rect>
          <text x={x + barWidth / 2} y="194" textAnchor="middle" className="chart-month">{month}</text>
        </g>;
      })}
    </svg>
  );
}

function MonthlyForecastChart({ months, metric }) {
  const actualKey = metric === "revenue" ? "actual_revenue" : metric === "expenses" ? "actual_expenses" : "actual_net_profit";
  const predictedKey = metric === "revenue" ? "predicted_revenue" : metric === "expenses" ? "predicted_expenses" : "predicted_net_profit";
  const values = months.flatMap((month) => [month[actualKey], month[predictedKey]]).filter((value) => value !== null && value !== undefined);
  const maximum = Math.max(1, ...values.map((value) => Math.abs(value)));
  const zeroY = 155;
  const scale = 110 / maximum;
  const barWidth = 28;
  return <svg className="monthly-forecast-chart" viewBox="0 0 650 220" role="img" aria-label={`Monthly ${metric} actuals and forecasts`}>
    <line x1="25" x2="630" y1={zeroY} y2={zeroY} className="chart-grid-line" />
    {months.map((month, index) => {
      const center = 75 + index * 125;
      const monthLabel = new Date(`${month.month}-01T00:00:00`).toLocaleDateString("en-IN", { month: "short", year: "2-digit" });
      const bars = month.status === "current"
        ? [{ key: actualKey, value: month[actualKey], kind: "actual", x: center - 31 }, { key: predictedKey, value: month[predictedKey], kind: "predicted", x: center + 3 }]
        : month.status === "actual"
          ? [{ key: actualKey, value: month[actualKey], kind: "actual", x: center - barWidth / 2 }]
          : [{ key: predictedKey, value: month[predictedKey], kind: "predicted", x: center - barWidth / 2 }];
      return <g key={month.month}>
        {bars.filter((bar) => bar.value !== null && bar.value !== undefined).map((bar) => {
          const height = Math.abs(bar.value) * scale;
          const y = bar.value >= 0 ? zeroY - height : zeroY;
          return <rect key={bar.key} x={bar.x} y={y} width={barWidth} height={Math.max(height, 1)} rx="3" className={`monthly-forecast-bar ${bar.kind}`}>
            <title>{`${monthLabel} ${bar.kind === "actual" ? "actual" : "predicted"} ${metric}: ${money(bar.value)}`}</title>
          </rect>;
        })}
        <text x={center} y="190" textAnchor="middle" className="chart-month">{monthLabel}</text>
      </g>;
    })}
  </svg>;
}

function AdminTablesPage() {
  const [tables, setTables] = useState([]);
  const [tableNumber, setTableNumber] = useState("");
  const [issuedQr, setIssuedQr] = useState(null);
  const [error, setError] = useState("");

  async function loadTables() {
    setTables(await api("/admin/tables"));
  }

  useEffect(() => {
    loadTables().catch((requestError) => setError(requestError.message));
  }, []);

  async function createTable(event) {
    event.preventDefault();
    setError("");
    try {
      const created = await api("/admin/tables", {
        method: "POST",
        body: JSON.stringify({ table_number: tableNumber.trim() }),
      });
      setTableNumber("");
      setIssuedQr(created);
      await loadTables();
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function issueQr(table) {
    setError("");
    try {
      setIssuedQr(await api(`/admin/tables/${table.id}/qr`, { method: "POST" }));
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function toggleTable(table) {
    setError("");
    try {
      await api(`/admin/tables/${table.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: !table.is_active }),
      });
      await loadTables();
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  const qrUrl = issuedQr ? new URL(issuedQr.order_url, window.location.origin).toString() : "";
  return <section className="reports-page">
    <div className="page-heading"><div><div className="eyebrow">DINE-IN · QR ORDERING</div><h1>Restaurant tables</h1><p>Create a secure, unique customer ordering QR code for each table.</p></div></div>
    {error && <div className="login-error">{error}</div>}
    <form className="table-create-form" onSubmit={createTable}><label className="form-field">Table number<input value={tableNumber} onChange={(event) => setTableNumber(event.target.value)} placeholder="Table 12" pattern="Table \d{1,3}" required /></label><button className="primary-button">Create table <Icon name="plus" size={16} /></button></form>
    {issuedQr && <article className="qr-issued-card"><div className="qr-print">
      <QRCodeSVG value={qrUrl} size={220} level="H" includeMargin />
      <strong>{issuedQr.table_number}</strong><span>Scan to browse and place an order</span>
    </div><div><h2>QR code ready</h2><p>Print or save this QR code for {issuedQr.table_number}. Its secret token is shown only once; reissuing it invalidates the previous code.</p><button className="primary-button" onClick={() => window.print()}>Print QR code</button></div></article>}
    <div className="table-card"><div className="table-title-row"><div><h2>Configured tables</h2><span>Manage active ordering codes.</span></div></div>
      {tables.length === 0 ? <div className="employee-empty">No tables configured yet.</div> : <div className="admin-table-list">{tables.map((table) => <article key={table.id}><div><strong>{table.table_number}</strong><span>{table.is_active ? "Accepting orders" : "Inactive"}</span></div><div><button className="secondary-button" disabled={!table.is_active} onClick={() => issueQr(table)}>Issue new QR</button><button className="cancel-button" onClick={() => toggleTable(table)}>{table.is_active ? "Deactivate" : "Activate"}</button></div></article>)}</div>}
    </div>
  </section>;
}

function CounterPaymentsPage() {
  const [unpaid, setUnpaid] = useState([]);
  const [cash, setCash] = useState({});
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [payingOrderId, setPayingOrderId] = useState(null);

  async function loadUnpaid() {
    setUnpaid(await api("/orders/unpaid"));
  }

  useEffect(() => {
    loadUnpaid().catch((requestError) => setError(requestError.message));
    const interval = window.setInterval(() => loadUnpaid().catch((requestError) => setError(requestError.message)), 10000);
    return () => window.clearInterval(interval);
  }, []);

  async function collectPayment(order) {
    const received = Number(cash[order.id] ?? order.total);
    setError("");
    setNotice("");
    setPayingOrderId(order.id);
    try {
      const result = await api(`/orders/${order.id}/pay`, {
        method: "POST",
        body: JSON.stringify({ cash_received: received }),
      });
      setNotice(`Order #${order.id} paid. Return ${money(result.change_due)} change.`);
      await loadUnpaid();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setPayingOrderId(null);
    }
  }

  function keepUnpaid(order) {
    setError("");
    setNotice(`Order #${order.id} is still unpaid.`);
  }

  return <section className="reports-page">
    <div className="page-heading"><div><div className="eyebrow">CUSTOMER QR ORDERS</div><h1>Counter payments</h1><p>Collect cash for dine-in QR orders and return the correct change.</p></div></div>
    {error && <div className="login-error">{error}</div>}{notice && <div className="customer-notice">{notice}</div>}
    <div className="table-card"><div className="table-title-row"><div><h2>Awaiting payment</h2><span>Orders disappear from this list after successful payment.</span></div></div>
      {unpaid.length === 0 ? <div className="employee-empty">No QR orders are waiting for payment.</div> : <div className="pending-payments">{unpaid.map((order) => <article key={order.id}>
        <div><strong>Order #{order.id} · {order.table_name} · Unpaid</strong><span>{order.customer_name || "Guest"} · {order.items.map((line) => `${line.quantity} × ${line.name}`).join(", ")}</span></div>
        <strong>{money(order.total)}</strong>
        <label className="form-field">Cash received<input type="number" min={order.total} step="1" value={cash[order.id] ?? order.total} onChange={(event) => setCash((current) => ({ ...current, [order.id]: event.target.value }))} /></label>
        <div className="payment-decisions" role="group" aria-label={`Payment decision for order ${order.id}`}>
          <button className="cancel-button" disabled={payingOrderId === order.id} onClick={() => keepUnpaid(order)}>No, still unpaid</button>
          <button className="primary-button" disabled={payingOrderId === order.id} onClick={() => collectPayment(order)}>{payingOrderId === order.id ? "Saving..." : "Yes, paid"}</button>
        </div>
      </article>)}</div>}
    </div>
  </section>;
}

function InventoryPage() {
  const [ingredients, setIngredients] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [menu, setMenu] = useState([]);
  const [recipeItemId, setRecipeItemId] = useState("");
  const [recipeLines, setRecipeLines] = useState([{ ingredient_id: "", quantity_per_item: "" }]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function loadInventory() {
    const [stock, history, items] = await Promise.all([
      api("/admin/inventory"),
      api("/admin/inventory/transactions"),
      api("/menu"),
    ]);
    setIngredients(stock);
    setTransactions(history);
    setMenu(items);
  }

  useEffect(() => {
    loadInventory().catch((requestError) => setError(requestError.message));
  }, []);

  async function createIngredient(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await api("/admin/inventory", {
        method: "POST",
        body: JSON.stringify({
          name: String(form.get("name")).trim(),
          unit: String(form.get("unit")).trim(),
          quantity: Number(form.get("quantity")),
          minimum_quantity: Number(form.get("minimum_quantity")),
          expires_at: String(form.get("expires_at")) || null,
        }),
      });
      event.currentTarget.reset();
      setNotice("Ingredient added to inventory");
      await loadInventory();
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function adjustIngredient(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await api(`/admin/inventory/${form.get("ingredient_id")}/adjust`, {
        method: "POST",
        body: JSON.stringify({
          quantity_delta: Number(form.get("quantity_delta")),
          reason: String(form.get("reason")).trim(),
        }),
      });
      event.currentTarget.reset();
      setNotice("Inventory adjustment recorded");
      await loadInventory();
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function saveRecipe(event) {
    event.preventDefault();
    const validLines = recipeLines.filter((line) => line.ingredient_id && Number(line.quantity_per_item) > 0);
    if (!recipeItemId || validLines.length === 0) {
      setError("Choose a menu item and add at least one ingredient to its recipe");
      return;
    }
    try {
      await api(`/admin/menu/${recipeItemId}/recipe`, {
        method: "PUT",
        body: JSON.stringify({
          ingredients: validLines.map((line) => ({
            ingredient_id: Number(line.ingredient_id),
            quantity_per_item: Number(line.quantity_per_item),
          })),
        }),
      });
      setNotice("Recipe saved. Stock is deducted transactionally when the item is ordered.");
      setRecipeLines([{ ingredient_id: "", quantity_per_item: "" }]);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function selectRecipeItem(menuItemId) {
    setRecipeItemId(menuItemId);
    if (!menuItemId) {
      setRecipeLines([{ ingredient_id: "", quantity_per_item: "" }]);
      return;
    }
    try {
      const recipe = await api(`/admin/menu/${menuItemId}/recipe`);
      setRecipeLines(recipe.ingredients.length ? recipe.ingredients.map((line) => ({
        ingredient_id: String(line.ingredient_id),
        quantity_per_item: line.quantity_per_item,
      })) : [{ ingredient_id: "", quantity_per_item: "" }]);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  return <section className="reports-page">
    <div className="page-heading"><div><div className="eyebrow">STOCK CONTROL</div><h1>Inventory & recipes</h1><p>Record ingredients and define recipe quantities to deduct stock for each order.</p></div></div>
    {error && <div className="login-error" role="alert">{error}</div>}{notice && <div className="customer-notice">{notice}</div>}
    <div className="inventory-forms">
      <form className="table-card inventory-form" onSubmit={createIngredient}><h2>Add ingredient</h2>
        <label className="form-field">Ingredient<input name="name" required maxLength="120" /></label>
        <div className="form-split"><label className="form-field">Unit<input name="unit" placeholder="kg, litre, piece" required maxLength="24" /></label><label className="form-field">Opening quantity<input name="quantity" type="number" min="0" step="0.001" required /></label></div>
        <div className="form-split"><label className="form-field">Low-stock threshold<input name="minimum_quantity" type="number" min="0" step="0.001" defaultValue="0" /></label><label className="form-field">Expiry date<input name="expires_at" type="date" /></label></div>
        <button className="primary-button">Add ingredient</button>
      </form>
      <form className="table-card inventory-form" onSubmit={adjustIngredient}><h2>Restock inventory</h2>
        <label className="form-field">Ingredient<select name="ingredient_id" required defaultValue=""><option value="" disabled>Select ingredient</option>{ingredients.map((item) => <option key={item.id} value={item.id}>{item.name} ({item.unit})</option>)}</select></label>
        <label className="form-field">Quantity change (+ restock, − waste)<input name="quantity_delta" type="number" step="0.001" required /></label>
        <label className="form-field">Reason<input name="reason" required maxLength="160" placeholder="Supplier delivery or waste" /></label>
        <button className="primary-button">Record adjustment</button>
      </form>
    </div>
    <form className="table-card recipe-editor" onSubmit={saveRecipe}><div className="table-title-row"><div><h2>Configure an item recipe</h2><span>Stock deduction uses these amounts per menu item.</span></div></div>
      <label className="form-field">Menu item<select value={recipeItemId} onChange={(event) => selectRecipeItem(event.target.value)} required><option value="">Select menu item</option>{menu.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
      {recipeLines.map((line, index) => <div className="form-split recipe-line" key={index}><label className="form-field">Ingredient<select value={line.ingredient_id} onChange={(event) => setRecipeLines((current) => current.map((entry, rowIndex) => rowIndex === index ? { ...entry, ingredient_id: event.target.value } : entry))}><option value="">Select ingredient</option>{ingredients.map((item) => <option key={item.id} value={item.id}>{item.name} ({item.unit})</option>)}</select></label><label className="form-field">Quantity per item<input type="number" min="0.001" step="0.001" value={line.quantity_per_item} onChange={(event) => setRecipeLines((current) => current.map((entry, rowIndex) => rowIndex === index ? { ...entry, quantity_per_item: event.target.value } : entry))} /></label>{recipeLines.length > 1 && <button type="button" className="cancel-button" onClick={() => setRecipeLines((current) => current.filter((_, rowIndex) => rowIndex !== index))}>Remove</button>}</div>)}
      <div className="recipe-actions"><button type="button" className="secondary-button" onClick={() => setRecipeLines((current) => [...current, { ingredient_id: "", quantity_per_item: "" }])}>Add ingredient</button><button className="primary-button">Save recipe</button></div>
    </form>
    <div className="table-card"><div className="table-title-row"><div><h2>Current stock</h2><span>Stock is deducted on successful order creation for configured recipes.</span></div></div>
      <div className="inventory-list">{ingredients.map((item) => <article key={item.id} className={item.low_stock || item.expired ? "inventory-alert" : ""}><div><strong>{item.name}</strong><span>{item.low_stock ? "Low stock" : "In stock"}{item.expired ? " · Expired" : ""}</span></div><strong>{Number(item.quantity).toLocaleString()} {item.unit}</strong><small>Minimum: {Number(item.minimum_quantity).toLocaleString()} {item.unit}</small></article>)}</div>
    </div>
    <div className="table-card"><div className="table-title-row"><div><h2>Inventory transactions</h2><span>Most recent 100 stock changes.</span></div></div>
      <div className="inventory-list">{transactions.map((entry) => <article key={entry.id}><div><strong>{entry.ingredient_name}</strong><span>{entry.reason}</span></div><strong>{Number(entry.quantity_delta) > 0 ? "+" : ""}{Number(entry.quantity_delta)} {entry.unit}</strong><small>{new Date(entry.created_at).toLocaleString()}</small></article>)}</div>
    </div>
  </section>;
}

function AnalyticsPage() {
  const today = localDateValue();
  const startDefault = localDateValue(new Date(Date.now() - 6 * 86400000));
  const [startDate, setStartDate] = useState(startDefault);
  const [endDate, setEndDate] = useState(today);
  const [analytics, setAnalytics] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setAnalytics(null);
    setError("");
    api(`/reports/analytics?start_date=${startDate}&end_date=${endDate}`)
      .then(setAnalytics)
      .catch((requestError) => setError(requestError.message));
  }, [startDate, endDate]);

  async function downloadCsv() {
    setError("");
    try {
      const response = await fetch(`/api/reports/export.csv?start_date=${startDate}&end_date=${endDate}`, {
        headers: { Authorization: `Bearer ${window.localStorage.getItem("restaurant-token")}` },
      });
      if (!response.ok) {
        const payload = await response.json();
        throw new Error(payload.detail || `Request failed (${response.status})`);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `restaurant-orders-${startDate}-to-${endDate}.csv`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  const maxSales = Math.max(1, ...(analytics?.daily_sales || []).map((day) => day.sales));
  return <section className="reports-page">
    <div className="page-heading reports-heading"><div><div className="eyebrow">BUSINESS INTELLIGENCE</div><h1>Sales analytics</h1><p>Explore paid sales, product trends, and raw order data for any selected period.</p></div>
      <div className="analytics-dates"><label className="report-date">From<input type="date" value={startDate} max={today} onChange={(event) => setStartDate(event.target.value)} /></label><label className="report-date">To<input type="date" value={endDate} max={today} onChange={(event) => setEndDate(event.target.value)} /></label></div>
    </div>
    {error && <div className="login-error">{error}</div>}
    {!analytics ? <div className="report-loading">Loading business data...</div> : <>
      <div className="report-summary"><article className="report-metric"><span>Paid sales</span><strong>{money(analytics.sales_revenue)}</strong><small>Before tax</small></article><article className="report-metric"><span>Paid orders</span><strong>{analytics.paid_order_count}</strong><small>{analytics.order_count} total orders placed</small></article><article className="report-metric"><span>Unpaid at counter</span><strong>{money(analytics.unpaid_total)}</strong><small>Not counted as revenue yet</small></article></div>
      <div className="table-card analytics-card"><div className="table-title-row"><div><h2>Daily sales</h2><span>Paid order revenue by date.</span></div><button className="secondary-button" onClick={downloadCsv}>Export raw CSV</button></div>
        <div className="analytics-chart">{analytics.daily_sales.map((day) => <div key={day.date} className="analytics-bar-group"><div className="analytics-bar" style={{ height: `${Math.max(3, (day.sales / maxSales) * 170)}px` }} title={money(day.sales)} /><span>{new Date(`${day.date}T00:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}</span></div>)}</div>
      </div>
      <div className="inventory-forms"><div className="table-card"><div className="table-title-row"><div><h2>Top-selling products</h2><span>Ranked by units sold in paid orders.</span></div></div>{analytics.top_items.map((item) => <article className="analytics-list-row" key={item.name}><strong>{item.name}</strong><span>{item.units} units</span><strong>{money(item.revenue)}</strong></article>)}</div>
        <div className="table-card"><div className="table-title-row"><div><h2>Sales by category</h2><span>Revenue from paid orders.</span></div></div>{analytics.category_sales.map((item) => <article className="analytics-list-row" key={item.category}><strong>{item.category}</strong><strong>{money(item.revenue)}</strong></article>)}</div></div>
    </>}
  </section>;
}

function StaffApp() {
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authError, setAuthError] = useState("");
  const [page, setPage] = useState("orders");
  const searchInputRef = useRef(null);
  const [items, setItems] = useState([]);
  const [orders, setOrders] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [cart, setCart] = useState([]);
  const [meal, setMeal] = useState("lunch");
  const [category, setCategory] = useState("All items");
  const [search, setSearch] = useState("");
  const [orderType, setOrderType] = useState("Dine in");
  const [table, setTable] = useState("Table 01");
  const [cash, setCash] = useState("");
  const [modal, setModal] = useState(null);
  const [editing, setEditing] = useState(null);
  const [notice, setNotice] = useState("");
  const [guestName, setGuestName] = useState("");
  const [orderNote, setOrderNote] = useState("");
  const [orderNumber, setOrderNumber] = useState(null);
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [paymentPromptItem, setPaymentPromptItem] = useState(null);
  const [reportDate, setReportDate] = useState(localDateValue());
  const [dailyReport, setDailyReport] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [monthlyForecast, setMonthlyForecast] = useState(null);
  const [forecastMetric, setForecastMetric] = useState("revenue");
  const [previousOrdersPage, setPreviousOrdersPage] = useState(0);
  const [prepOrders, setPrepOrders] = useState([]);
  const previousMonthOrders = forecast?.previous_month.orders ?? [];
  const previousOrdersPageSize = 25;
  const previousOrdersPageCount = Math.ceil(previousMonthOrders.length / previousOrdersPageSize);
  const previousOrdersStart = previousOrdersPage * previousOrdersPageSize;
  const visiblePreviousMonthOrders = previousMonthOrders.slice(
    previousOrdersStart,
    previousOrdersStart + previousOrdersPageSize,
  );

  useEffect(() => {
    if (!window.localStorage.getItem("restaurant-token")) {
      setAuthLoading(false);
      return;
    }
    api("/auth/me")
      .then(setUser)
      .catch((error) => {
        window.localStorage.removeItem("restaurant-token");
        setAuthError(error.message);
      })
      .finally(() => setAuthLoading(false));
  }, []);

  useEffect(() => {
    if (!user) return;
    if (user.role === "staff" && user.employee_type === "kitchen") {
      setPage("kitchen");
      return;
    }
    const requests = user.role === "admin"
      ? Promise.all([api("/menu"), api("/orders"), api("/admin/employees")])
      : Promise.all([api("/menu")]);
    requests
      .then((result) => {
        const [menu, orderList = [], employeeList = []] = result;
        setItems(menu);
        setOrders(orderList);
        setEmployees(employeeList);
      })
      .catch((error) => setNotice(`Could not load restaurant data: ${error.message}`));
  }, [user]);

  useEffect(() => {
    if (!user || (user.role !== "admin" && !["kitchen", "reception"].includes(user.employee_type)) || page !== "kitchen") return undefined;
    let active = true;
    const loadPrepOrders = () => api("/prep/orders")
      .then((result) => { if (active) setPrepOrders(result); })
      .catch((error) => { if (active) setNotice(`Could not load kitchen orders: ${error.message}`); });
    loadPrepOrders();
    const token = window.localStorage.getItem("restaurant-token");
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const socket = new WebSocket(`${protocol}//${window.location.host}/ws/kitchen`, ["restaurant-auth", token || ""]);
    socket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === "prep.updated" || message.type === "order.created") loadPrepOrders();
    };
    const interval = window.setInterval(loadPrepOrders, 30000);
    return () => { active = false; socket.close(); window.clearInterval(interval); };
  }, [user, page]);

  useEffect(() => {
    if (page !== "orders" || modal) return undefined;
    function focusMenuSearch(event) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        searchInputRef.current?.focus();
        searchInputRef.current?.select();
      }
    }
    window.addEventListener("keydown", focusMenuSearch);
    return () => window.removeEventListener("keydown", focusMenuSearch);
  }, [page, modal]);

  useEffect(() => {
    if (!user || user.role !== "admin" || page !== "reports") return;
    let active = true;
    const loadReport = () => api(`/reports/daily?report_date=${reportDate}`)
      .then((report) => { if (active) setDailyReport(report); })
      .catch((error) => { if (active) setNotice(`Could not load daily report: ${error.message}`); });
    setDailyReport(null);
    loadReport();
    const interval = window.setInterval(loadReport, 15000);
    return () => { active = false; window.clearInterval(interval); };
  }, [user, page, reportDate]);

  useEffect(() => {
    if (!user || user.role !== "admin" || page !== "forecast") return;
    setForecast(null);
    setMonthlyForecast(null);
    setPreviousOrdersPage(0);
    api("/reports/forecast")
      .then(setForecast)
      .catch((error) => setNotice(`Could not load sales forecast: ${error.message}`));
    api("/reports/forecast/monthly")
      .then(setMonthlyForecast)
      .catch((error) => setNotice(`Could not load the monthly forecast: ${error.message}`));
  }, [user, page]);

  const visibleItems = useMemo(() => items.filter((item) =>
    (meal === "breakfast" ? item.category === "Breakfast" : item.category !== "Breakfast") &&
    (category === "All items" || item.category === category) &&
    `${item.name} ${item.description}`.toLowerCase().includes(search.toLowerCase())
  ), [items, meal, category, search]);
  const subtotal = cart.reduce((sum, line) => sum + line.price * line.quantity, 0);
  const tax = Math.round(subtotal * 0.05);
  const total = subtotal + tax;
  const change = Math.max(0, Number(cash || 0) - total);

  function addToCart(item) {
    setCart((current) => {
      const found = current.find((line) => line.id === item.id);
      return found
        ? current.map((line) => line.id === item.id ? { ...line, quantity: line.quantity + 1 } : line)
        : [...current, { ...item, quantity: 1 }];
    });
  }

  function updateQuantity(id, amount) {
    setCart((current) => current
      .map((line) => line.id === id ? { ...line, quantity: line.quantity + amount } : line)
      .filter((line) => line.quantity > 0));
  }

  function startNewOrder() {
    setCart([]);
    setCash("");
    setGuestName("");
    setOrderNote("");
    setOrderNumber(null);
    setNotice("");
  }

  async function completeOrder() {
    if (!cart.length || Number(cash) < total) return;
    try {
      const order = await api("/orders", {
        method: "POST",
        body: JSON.stringify({
          order_type: orderType,
          table_name: orderType === "Dine in" ? table : null,
          guest_name: guestName || null,
          note: orderNote,
          cash_received: Number(cash),
          items: cart.map((line) => ({ item_id: line.id, quantity: line.quantity })),
        }),
      });
      setOrderNumber(order.id);
      setNotice(`Order #${order.id} placed · Return ${money(order.change_due)} to the customer`);
      if (user.employee_type !== "kitchen") {
        api("/prep/orders").then(setPrepOrders).catch((error) => setNotice(`Order was saved, but kitchen status could not be refreshed: ${error.message}`));
      }
      setOrders((current) => [order, ...current]);
      setCart([]);
      setCash("");
      setGuestName("");
      setOrderNote("");
      window.setTimeout(() => setNotice(""), 5000);
    } catch (error) {
      setNotice(`Could not place order: ${error.message}`);
    }
  }

  async function advancePrepItem(item) {
    const nextStatus = item.prep_status === "queued"
      ? "preparing"
      : item.prep_status === "preparing" ? "ready" : "delivered";
    try {
      await api(`/prep/items/${item.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: nextStatus }),
      });
      setPrepOrders((current) => current
        .map((order) => ({
          ...order,
          items: nextStatus === "delivered"
            ? order.items.filter((line) => line.id !== item.id)
            : order.items.map((line) => line.id === item.id ? { ...line, prep_status: nextStatus } : line),
        }))
        .filter((order) => order.items.length > 0));
      setPaymentPromptItem(null);
    } catch (error) {
      setNotice(`Could not update kitchen checklist: ${error.message}`);
    }
  }

  function showPaymentPrompt(item, order) {
    setPaymentPromptItem({ ...item, order_total: order.total });
  }

  async function confirmOrderPayment(paid) {
    const item = paymentPromptItem;
    if (!item) return;
    if (!paid) {
      setPaymentPromptItem(null);
      return;
    }
    try {
      await api(`/orders/${item.order_id}/confirm-payment`, {
        method: "POST",
        body: JSON.stringify({ paid: true }),
      });
      setPrepOrders((current) => current.map((order) => order.id === item.order_id
        ? { ...order, payment_status: "paid" }
        : order));
      setNotice(`Order #${item.order_id} marked paid`);
      setPaymentPromptItem(null);
    } catch (error) {
      setNotice(`Could not confirm payment: ${error.message}`);
    }
  }

  function handlePrepAction(item) {
    advancePrepItem(item);
  }

  async function saveMenuItem(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const item = {
      name: String(form.get("name")).trim(),
      category: String(form.get("category")),
      price: Number(form.get("price")),
      cost_price: String(form.get("cost_price") ?? "") === "" ? null : Number(form.get("cost_price")),
      description: String(form.get("description")).trim(),
      popular: editing?.popular ?? false,
      image: editing?.image ?? "photo-1546833999-b9f581a1996d",
      ingredients_text: String(form.get("ingredients_text")).trim(),
      allergens_text: String(form.get("allergens_text")).trim(),
      dietary_tags: form.getAll("dietary_tags").map(String),
      dietary_verified: form.get("dietary_verified") === "on",
      spice_level: String(form.get("spice_level") ?? "") === "" ? null : Number(form.get("spice_level")),
      calories: String(form.get("calories") ?? "") === "" ? null : Number(form.get("calories")),
    };
    if (!item.name || !Number.isFinite(item.price) || item.price <= 0) return;
    try {
      const saved = await api(editing ? `/menu/${editing.id}` : "/menu", {
        method: editing ? "PUT" : "POST",
        body: JSON.stringify(item),
      });
      setItems((current) => editing
        ? current.map((existing) => existing.id === editing.id ? saved : existing)
        : [...current, saved]);
      setModal(null);
      setEditing(null);
      setNotice(`Menu item ${editing ? "updated" : "added"}`);
    } catch (error) {
      setNotice(`Could not save menu item: ${error.message}`);
    }
  }

  async function removeMenuItem(id) {
    try {
      await api(`/menu/${id}`, { method: "DELETE" });
      setItems((current) => current.filter((item) => item.id !== id));
      setCart((current) => current.filter((line) => line.id !== id));
    } catch (error) {
      setNotice(`Could not delete menu item: ${error.message}`);
    }
  }

  async function saveEmployee(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const employee = await api("/admin/employees", {
        method: "POST",
        body: JSON.stringify({
          username: String(form.get("username")).trim(),
          display_name: String(form.get("display_name")).trim(),
          password: String(form.get("password")),
          employee_type: String(form.get("employee_type")),
        }),
      });
      setEmployees((current) => [...current, employee].sort((a, b) => a.username.localeCompare(b.username)));
      setModal(null);
      setNotice(`Employee account "${employee.username}" created`);
    } catch (error) {
      setNotice(`Could not create employee: ${error.message}`);
    }
  }

  async function toggleEmployeeStatus(employee) {
    try {
      const updated = await api(`/admin/employees/${employee.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: !employee.is_active }),
      });
      setEmployees((current) => current.map((item) => item.id === updated.id ? updated : item));
      setNotice(`Employee "${employee.username}" ${updated.is_active ? "enabled" : "disabled"}`);
    } catch (error) {
      setNotice(`Could not update employee: ${error.message}`);
    }
  }

  async function saveEmployeePassword(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await api(`/admin/employees/${selectedEmployee.id}/password`, {
        method: "PUT",
        body: JSON.stringify({ password: String(form.get("password")) }),
      });
      setModal(null);
      setSelectedEmployee(null);
      setNotice(`Password reset for "${selectedEmployee.username}"`);
    } catch (error) {
      setNotice(`Could not reset employee password: ${error.message}`);
    }
  }

  async function signOut() {
    try {
      await api("/auth/logout", { method: "POST" });
      setAuthError("");
    } catch (error) {
      setAuthError(`Signed out locally; server session could not be revoked: ${error.message}`);
    } finally {
      window.localStorage.removeItem("restaurant-token");
      setUser(null);
      setItems([]);
      setOrders([]);
      setEmployees([]);
      setCart([]);
      setPage("orders");
    }
  }

  if (authLoading) return <div className="login-screen"><div className="login-loading">Connecting to restaurant...</div></div>;
  if (!user) return <LoginScreen onLogin={setUser} initialError={authError} />;

  const adminView = user.role === "admin" && page === "menu";
  const employeeView = user.role === "admin" && page === "employees";
  const reportsView = user.role === "admin" && page === "reports";
  const forecastView = user.role === "admin" && page === "forecast";
  const analyticsView = user.role === "admin" && page === "analytics";
  const assistantView = user.role === "admin" && page === "assistant";
  const kitchenView = page === "kitchen" && (user.role === "admin" || ["kitchen", "reception"].includes(user.employee_type));

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">S<span>.</span></div>
          <div><div className="brand-name">saffron<span>&</span>stone</div><div className="brand-caption">RESTAURANT</div></div>
        </div>
        <div className="workspace-label">WORKSPACE</div>
        <nav className="side-nav">
          {(user.role === "admin" || user.employee_type === "reception") && <button className={`nav-link ${page === "orders" ? "active" : ""}`} onClick={() => setPage("orders")}><Icon name="grid" /><span>New order</span><kbd>⌘ 1</kbd></button>}
          {user.role === "admin" && <button className={`nav-link ${page === "menu" ? "active" : ""}`} onClick={() => setPage("menu")}><Icon name="menu" /><span>Menu & pricing</span></button>}
          {user.role === "admin" && <button className={`nav-link ${page === "employees" ? "active" : ""}`} onClick={() => setPage("employees")}><Icon name="users" /><span>Employees</span></button>}
          {user.role === "admin" && <button className={`nav-link ${page === "reports" ? "active" : ""}`} onClick={() => setPage("reports")}><Icon name="receipt" /><span>Daily reports</span></button>}
          {user.role === "admin" && <button className={`nav-link ${page === "analytics" ? "active" : ""}`} onClick={() => setPage("analytics")}><Icon name="sparkle" /><span>Business analytics</span></button>}
          {user.role === "admin" && <button className={`nav-link ${page === "forecast" ? "active" : ""}`} onClick={() => setPage("forecast")}><Icon name="sparkle" /><span>Sales forecast</span></button>}
          {user.role === "admin" && <button className={`nav-link ${page === "assistant" ? "active" : ""}`} onClick={() => setPage("assistant")} aria-label="AI business assistant"><Icon name="sparkle" /><span>AI business assistant</span></button>}
          {(user.role === "admin" || ["kitchen", "reception"].includes(user.employee_type)) && <button className={`nav-link ${page === "kitchen" ? "active" : ""}`} onClick={() => setPage("kitchen")}><Icon name="check" /><span>{user.employee_type === "kitchen" ? "Kitchen board" : "Kitchen tracking"}</span></button>}
          {user.role === "admin" && <button className={`nav-link ${page === "history" ? "active" : ""}`} onClick={() => setPage("history")}><Icon name="receipt" /><span>Order history</span></button>}
        </nav>
        <div className="sidebar-bottom">
          <div className="shift-card">
            <div className="shift-icon"><Icon name="clock" size={16} /></div>
            <div><div className="shift-title">{mealServices.find((service) => service.id === meal)?.name} service</div><div className="shift-time">{mealServices.find((service) => service.id === meal)?.time}</div></div>
            <span className="live-dot" />
          </div>
          <div className="profile">
            <div className="avatar">{user.display_name.split(" ").map((part) => part[0]).join("").slice(0, 2)}</div>
            <div className="profile-copy"><strong>{user.display_name}</strong><span>{user.role === "admin" ? "Administrator" : user.employee_type === "kitchen" ? "Kitchen staff" : "Reception staff"}</span></div>
            <button className="logout-button" onClick={signOut} title="Log out" aria-label="Log out"><Icon name="logout" size={16} /><span>Log out</span></button>
          </div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumb"><span>Workspace</span><span className="crumb-slash">/</span><strong>{adminView ? "Menu & pricing" : employeeView ? "Employees" : analyticsView ? "Business analytics" : reportsView ? "Daily reports" : forecastView ? "Sales forecast" : assistantView ? "AI business assistant" : kitchenView ? "Kitchen tracking" : page === "history" ? "Order history" : "New order"}</strong></div>
          <div className="topbar-right">
            <span className="service-status"><span className="live-dot" /> Service is live</span>
            <span className="topbar-divider" />
            <div className="date-label">{new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" })}</div>
            <button className="help-button" aria-label="Help">?</button>
          </div>
        </header>

        {assistantView ? <AdminChat user={user} /> : analyticsView ? <AnalyticsPage /> : reportsView ? (
          <section className="reports-page">
            <div className="page-heading reports-heading">
              <div><div className="eyebrow">DAILY BUSINESS SUMMARY</div><h1>Sales & profit</h1><p>Review saved orders, cash totals, and gross profit by day.</p></div>
              <label className="report-date">Report date<input type="date" value={reportDate} max={localDateValue()} onChange={(event) => setReportDate(event.target.value)} /></label>
            </div>
            {!dailyReport ? <div className="report-loading">Loading daily records...</div> : <>
              {!dailyReport.profit_complete && <div className="profit-warning"><Icon name="sparkle" size={17} /><span><strong>Profit is incomplete.</strong> Set item costs in Menu & pricing to calculate gross profit. {dailyReport.uncosted_quantity} sold item(s) have no saved cost.</span></div>}
              {dailyReport.orders.some((order) => order.order_status !== "cancelled" && order.note?.startsWith("[DEMO SAMPLE]")) && <div className="profit-warning"><Icon name="sparkle" size={17} /><span><strong>Demo orders included.</strong> This date's sales totals include clearly labeled sample orders.</span></div>}
              <div className="report-summary">
                <article className="report-metric"><span>Orders placed</span><strong>{dailyReport.order_count}</strong><small>On {dailyReport.date}</small></article>
                <article className="report-metric"><span>Sales revenue <small>before tax</small></span><strong>{money(dailyReport.sales_revenue)}</strong><small>Tax collected: {money(dailyReport.tax_collected)}</small></article>
                <article className="report-metric"><span>Cost of goods</span><strong>{money(dailyReport.cost_of_goods)}</strong><small>{dailyReport.profit_complete ? "All item costs recorded" : `${dailyReport.uncosted_quantity} item(s) missing cost`}</small></article>
                <article className={`report-metric profit-metric ${dailyReport.profit_complete ? "" : "incomplete"}`}><span>Gross profit <small>before overhead</small></span><strong>{dailyReport.gross_profit === null ? "Incomplete" : money(dailyReport.gross_profit)}</strong><small>Sales revenue minus item costs</small></article>
              </div>
              <div className="report-cash-strip"><span>Paid total <strong>{money(dailyReport.total_billed)}</strong></span><span>Cash received <strong>{money(dailyReport.cash_received)}</strong></span><span>Change returned <strong>{money(dailyReport.change_given)}</strong></span>{dailyReport.unpaid_order_count > 0 && <span>Unpaid at counter <strong>{money(dailyReport.unpaid_total)}</strong></span>}</div>
              <div className="table-card report-orders-card">
                <div className="table-title-row"><div><h2>Orders for {dailyReport.date}</h2><span>Order and cashier records for the selected date.</span></div></div>
                {dailyReport.orders.length === 0 ? <div className="employee-empty">No orders were saved for this date.</div> :
                  <div className="report-orders">{dailyReport.orders.map((order) => {
                    const orderCostComplete = order.items.every((line) => line.cost_price !== null);
                    const orderCost = order.items.reduce((sum, line) => sum + (line.cost_price ?? 0) * line.quantity, 0);
                    return <article className="report-order" key={order.id}>
                      <div className="report-order-main"><strong>Order #{order.id} {order.note?.startsWith("[DEMO SAMPLE]") && <em className="demo-order-badge">DEMO</em>} <span>{order.order_type}{order.table_name ? ` · ${order.table_name}` : ""} · {order.payment_status}{order.order_status === "cancelled" ? " · CANCELLED" : ""}</span></strong><small>{order.items.map((line) => `${line.quantity} × ${line.name}`).join(", ")}</small>{order.cancellation_reason && <small>Cancellation reason: {order.cancellation_reason}</small>}{order.guest_name && <small>Guest: {order.guest_name}</small>}{order.note && <small className="demo-order-note">{order.note}</small>}<small>Placed by {order.staff_name} · {new Date(order.created_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}</small></div>
                      <div className="report-order-amount"><span>Bill</span><strong>{money(order.total)}</strong></div>
                      <div className="report-order-amount"><span>Gross profit</span><strong>{order.order_status === "cancelled" ? "Cancelled" : order.payment_status !== "paid" ? "Not paid" : orderCostComplete ? money(order.subtotal - orderCost) : "Incomplete"}</strong></div>
                    </article>;
                  })}</div>}
              </div>
              <p className="report-footnote">Gross profit excludes GST and operating expenses. It uses each item's cost saved at the time of sale; older orders without cost records are marked incomplete.</p>
            </>}
          </section>
        ) : forecastView ? (
          <section className="reports-page forecast-page">
            <div className="page-heading reports-heading"><div><div className="eyebrow">SALES OUTLOOK</div><h1>Future sales: Nov 2026 – Mar 2027</h1><p>Monthly revenue, expenses, and net profit based on past sales patterns.</p></div></div>
            {!monthlyForecast ? <div className="report-loading">Analyzing five months of sales...</div> : <>
              {monthlyForecast.demo_order_count > 0 && <div className="profit-warning"><Icon name="sparkle" size={17} /><span><strong>Sample orders are included in the historical data.</strong> {monthlyForecast.demo_order_count} demo order(s) may affect actual totals and predictions.</span></div>}
              <div className="forecast-explainer"><strong>Actual vs predicted</strong><span>Green shows recorded actuals. Gold shows estimates. November combines sales so far with the estimate for the rest of the month when it is still in progress. Predictions use historical sales, weekends, Indian festival seasons, and recorded expenses. Recent sales trend adjustment: {monthlyForecast.trend_adjustment_percent > 0 ? "+" : ""}{monthlyForecast.trend_adjustment_percent}%.</span></div>
              <div className="table-card monthly-forecast-card">
                <div className="table-title-row"><div><h2>Monthly comparison</h2><span>Hover over chart bars for exact values.</span></div>
                  <label className="forecast-metric-select">Show<select value={forecastMetric} onChange={(event) => setForecastMetric(event.target.value)}><option value="revenue">Revenue</option><option value="expenses">Expenses</option><option value="profit">Net profit</option></select></label>
                </div>
                <div className="chart-legend monthly-chart-legend"><span><i className="actual-key" /> Actual</span><span><i className="forecast-key" /> Predicted / remaining</span></div>
                <div className="monthly-forecast-chart-wrap"><MonthlyForecastChart months={monthlyForecast.months} metric={forecastMetric} /></div>
                <div className="monthly-forecast-table-wrap"><table className="monthly-forecast-table"><thead><tr><th>Month</th><th>Actual sales</th><th>Predicted sales</th><th>Projected revenue</th><th>Expenses</th><th>Net profit</th></tr></thead>
                  <tbody>{monthlyForecast.months.map((month) => <tr key={month.month}>
                    <th>{new Date(`${month.month}-01T00:00:00`).toLocaleDateString("en-IN", { month: "long", year: "numeric" })}<small className={`forecast-status ${month.status}`}>{month.status === "actual" ? "Actual" : month.status === "current" ? "Actual + estimate" : "Predicted"}</small>{month.festivals.length > 0 && <small className="forecast-festival">{month.festivals.join(", ")}</small>}</th>
                    <td>{month.actual_revenue === null ? "—" : money(month.actual_revenue)}{month.status === "current" && <small>to date</small>}</td>
                    <td>{month.predicted_revenue === null ? "—" : money(month.predicted_revenue)}{month.status === "current" && <small>remaining month</small>}</td>
                    <td>{money(month.projected_revenue)}</td><td>{money(month.projected_expenses)}<small>{month.expense_note}</small></td><td>{month.status === "actual" && !month.profit_complete ? "Incomplete" : money(month.projected_net_profit)}</td>
                  </tr>)}</tbody>
                </table></div>
                <p className="report-footnote">Revenue is before tax. Net profit is projected revenue minus food and operating expenses. Historical operating expenses with no recorded entry are not invented in the actuals. A forecast is an estimate, not a guarantee.</p>
              </div>
            </>}
            {!forecast ? <div className="report-loading">Analyzing recent sales...</div> : <>
              {forecast.festival_season && <div className="profit-warning"><Icon name="sparkle" size={17} /><span><strong>{forecast.festival_season} season.</strong> The estimate includes a possible seasonal sales increase.</span></div>}
              {forecast.demo_order_count > 0 && <div className="profit-warning"><Icon name="sparkle" size={17} /><span><strong>Sample orders are included.</strong> {forecast.demo_order_count} demo order(s) affect the estimate.</span></div>}
              <div className="table-title-row forecast-history-heading"><div><h2>Recent sales and menu trends</h2><span>Context behind the month-by-month outlook.</span></div></div>
              <div className="table-card forecast-chart-card">
                <div className="table-title-row"><div><h2>Sales over time</h2><span>See how sales have changed and what next month may look like.</span></div><div className="chart-legend"><span><i className="actual-key" /> Past sales</span><span><i className="current-key" /> This month estimate</span><span><i className="forecast-key" /> Next month estimate</span></div></div>
                <ForecastChart history={forecast.history} />
              </div>
              <div className="table-card forecast-raw-card">
                <div className="table-title-row"><div><h2>Last month’s orders</h2><span>Order-by-order sales records for {new Date(`${forecast.previous_month.month}-01T00:00:00`).toLocaleDateString("en-IN", { month: "long", year: "numeric" })}.</span></div><div className="forecast-raw-total"><strong>{money(forecast.previous_month.sales_revenue)}</strong><span>{forecast.previous_month.order_count} orders · before tax</span></div></div>
                {forecast.previous_month.orders.length === 0 ? <div className="employee-empty">No orders were recorded last month. Forecasts use the available 90-day order history.</div> :
                  <>
                    <div className="forecast-raw-orders">{visiblePreviousMonthOrders.map((order) => <article className="forecast-raw-order" key={order.id}>
                      <div><strong>Order #{order.id} {order.note?.startsWith("[DEMO SAMPLE]") && <em className="demo-order-badge">DEMO</em>}</strong><span>{new Date(`${String(order.created_at).replace(" ", "T")}Z`).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })} · {order.order_type}{order.table_name ? ` · ${order.table_name}` : ""}</span></div>
                      <small>{order.items.map((line) => `${line.quantity} × ${line.name}`).join(", ") || "No item details"}</small>
                      {order.note && <small className="demo-order-note">{order.note}</small>}
                      <span>Subtotal {money(order.subtotal)}</span><span>Tax {money(order.tax)}</span><strong>{money(order.total)}</strong>
                    </article>)}</div>
                    {previousOrdersPageCount > 1 && <div className="forecast-pagination">
                      <span>Showing {previousOrdersStart + 1}–{Math.min(previousOrdersStart + previousOrdersPageSize, previousMonthOrders.length)} of {previousMonthOrders.length} orders</span>
                      <div><button className="secondary-button" disabled={previousOrdersPage === 0} onClick={() => setPreviousOrdersPage((current) => current - 1)}>Previous</button><button className="secondary-button" disabled={previousOrdersPage + 1 >= previousOrdersPageCount} onClick={() => setPreviousOrdersPage((current) => current + 1)}>Next</button></div>
                    </div>}
                  </>}
              </div>
              <div className="table-card forecast-products-card">
                <div className="table-title-row"><div><h2>Popular items</h2><span>Most ordered recently, with a rough estimate for next month.</span></div></div>
                {forecast.best_sellers.length === 0 ? <div className="employee-empty">No paid order history yet. Popular items will appear as sales are recorded.</div> :
                  <div className="forecast-products">{forecast.best_sellers.map((item, index) => <div className="forecast-product" key={item.name}><span className="forecast-rank">{index + 1}</span><strong>{item.name}</strong><span>{item.sold_units} sold recently</span><b>About {item.forecast_units} next month</b></div>)}</div>}
              </div>
              <p className="report-footnote">Only paid orders count as sales. Future sales can differ from this estimate.</p>
            </>}
          </section>
        ) : kitchenView ? (
          <section className="menu-page kitchen-page">
            <div className="page-heading"><div><div className="eyebrow">{user.employee_type === "kitchen" ? "KITCHEN TEAM" : "LIVE ORDER TRACKING"}</div><h1>Kitchen progress</h1><p>Today's tickets update automatically as food moves through preparation.</p></div><span className="kitchen-live"><i /> Live · refreshes every 5 seconds</span></div>
            {prepOrders.length === 0 ? <div className="empty-history"><div className="empty-icon"><Icon name="check" size={24} /></div><h2>Kitchen queue is clear</h2><p>New orders will appear here. Delivered items are removed from active progress.</p></div> :
              <div className="kitchen-tickets">{prepOrders.map((order) => {
                const readyCount = order.items.filter((item) => item.prep_status === "ready").length;
                return <article className="kitchen-ticket" key={order.id}>
                  <header><div><strong>Order #{order.id}</strong><span>{order.order_type}{order.table_name ? ` · ${order.table_name}` : ""}{order.guest_name ? ` · ${order.guest_name}` : ""}</span></div><div className="ticket-progress"><strong>{readyCount}/{order.items.length} ready</strong><span>{order.staff_name} · {new Date(`${String(order.created_at).replace(" ", "T")}Z`).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}</span></div></header>
                  {order.note && <p className="ticket-note">Kitchen note: {order.note}</p>}
                  <div className="kitchen-checklist">{order.items.map((item) => <div className={`kitchen-item ${item.prep_status}`} key={item.id}>
                    <span className="check-box">{item.prep_status === "ready" ? <Icon name="check" size={14} /> : item.prep_status === "preparing" ? <Icon name="clock" size={14} /> : null}</span>
                    <strong>{item.quantity} × {item.name}</strong>
                    <span className={`prep-badge ${item.prep_status}`}>{item.prep_status === "queued" ? "Queued" : item.prep_status === "preparing" ? "Preparing" : "Ready"}</span>
                    {user.role === "staff" && user.employee_type === "kitchen" && <button className="prep-action" onClick={() => handlePrepAction(item)}>{item.prep_status === "queued" ? "Start making" : item.prep_status === "preparing" ? "Mark ready" : "Mark delivered"}</button>}
                    {(user.role === "admin" || user.employee_type === "reception") && item.prep_status === "ready" && order.payment_status !== "paid" && <button className="prep-action payment-action" onClick={() => showPaymentPrompt(item, order)}>Has customer paid?</button>}
                  </div>)}</div>
                </article>;
              })}</div>}
          </section>
        ) : user.role === "admin" && page === "history" ? (
          <section className="history-page">
            <div className="page-heading"><div><div className="eyebrow">YOUR SHIFT, AT A GLANCE</div><h1>Order history</h1><p>Recent orders from today's service.</p></div></div>
            {orders.length === 0 ? <div className="empty-history"><div className="empty-icon"><Icon name="receipt" size={24} /></div><h2>You're all caught up</h2><p>New orders will show up here once they're placed.</p><button className="primary-button" onClick={() => setPage("orders")}>Start a new order <Icon name="arrow" size={16} /></button></div> :
              <div className="history-list">{orders.map((order) => <article className={`history-order ${order.order_status === "cancelled" ? "cancelled-history-order" : ""}`} key={order.id}><div><strong>Order #{order.id} {order.order_status === "cancelled" ? "· CANCELLED" : ""}</strong><span>{order.order_type}{order.table_name ? ` · ${order.table_name}` : ""} · {new Date((order.created_at || new Date().toISOString()).replace(" ", "T") + "Z").toLocaleString("en-IN")}</span><small>{order.items.map((line) => `${line.quantity} × ${line.name}`).join(", ")}</small>{order.cancellation_reason && <small>Reason: {order.cancellation_reason}</small>}</div><div className="history-total"><strong>{money(order.total)}</strong><span>{order.payment_status === "paid" ? "Paid" : "Unpaid"} · Cash {money(order.cash_received)} · Change {money(order.change_due)}</span></div></article>)}</div>}
          </section>
        ) : adminView ? (
          <section className="menu-page">
            <div className="page-heading menu-heading">
              <div><div className="eyebrow">KEEP YOUR MENU UP TO DATE</div><h1>Menu & pricing</h1><p>Add dishes, update prices, and keep the team in sync.</p></div>
              <button className="primary-button" onClick={() => { setEditing(null); setModal("item"); }}><Icon name="plus" size={17} /> Add menu item</button>
            </div>
            <div className="menu-summary">
              <div className="summary-box"><div className="summary-icon green"><Icon name="menu" /></div><div><span>Total items</span><strong>{items.length}</strong></div></div>
              <div className="summary-box"><div className="summary-icon amber"><Icon name="leaf" /></div><div><span>Categories</span><strong>{new Set(items.map((item) => item.category)).size}</strong></div></div>
              <div className="summary-box"><div className="summary-icon blue"><Icon name="users" /></div><div><span>Staff roles</span><strong>Reception & kitchen</strong></div></div>
            </div>
            <div className="table-card">
              <div className="table-title-row"><div><h2>All menu items</h2><span>Changes are instantly available to your staff.</span></div><div className="menu-search"><Icon name="search" size={16} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Find an item..." /></div></div>
              <div className="menu-table">
                <div className="table-header"><span>ITEM</span><span>CATEGORY</span><span>PRICE</span><span>COST</span><span>STATUS</span><span /></div>
                {visibleItems.map((item) => <div className="table-row" key={item.id}>
                  <div className="item-cell"><img src={imageUrl(item.image)} alt="" /><div><strong>{item.name}</strong><span>{item.description}</span></div></div>
                  <div><span className="category-pill">{item.category}</span></div>
                  <div className="price-cell">{money(item.price)}</div>
                  <div className="price-cell">{item.cost_price === null ? "Not set" : money(item.cost_price)}</div>
                  <div><span className="availability"><i /> Available</span></div>
                  <div className="row-actions"><button title="Edit item" onClick={() => { setEditing(item); setModal("item"); }}><Icon name="edit" size={16} /></button><button title="Delete item" onClick={() => removeMenuItem(item.id)}><Icon name="trash" size={16} /></button></div>
                </div>)}
              </div>
            </div>
            <div className="admin-note"><Icon name="sparkle" size={17} /><span><strong>Good to know</strong> — Price updates apply to new orders. Orders already in progress keep their original price.</span></div>
          </section>
        ) : employeeView ? (
          <section className="menu-page">
            <div className="page-heading menu-heading">
              <div><div className="eyebrow">STAFF ACCESS</div><h1>Employees</h1><p>Create reception or kitchen logins and manage their access.</p></div>
              <button className="primary-button" onClick={() => setModal("employee")}><Icon name="plus" size={17} /> Add employee</button>
            </div>
            <div className="menu-summary">
              <div className="summary-box"><div className="summary-icon green"><Icon name="users" /></div><div><span>Total employees</span><strong>{employees.length}</strong></div></div>
              <div className="summary-box"><div className="summary-icon amber"><Icon name="check" /></div><div><span>Active accounts</span><strong>{employees.filter((employee) => employee.is_active).length}</strong></div></div>
              <div className="summary-box"><div className="summary-icon blue"><Icon name="receipt" /></div><div><span>Employee access</span><strong>Role-based</strong></div></div>
            </div>
            <div className="table-card">
              <div className="table-title-row"><div><h2>Employee accounts</h2><span>Reception staff take orders; kitchen staff manage preparation checklists.</span></div></div>
              <div className="employee-table">
                <div className="employee-row employee-header"><span>EMPLOYEE</span><span>USERNAME</span><span>WORK AREA</span><span>STATUS</span><span>ACTIONS</span></div>
                {employees.map((employee) => <div className="employee-row" key={employee.id}>
                  <div className="employee-name"><span className="avatar">{employee.display_name.split(" ").map((part) => part[0]).join("").slice(0, 2)}</span><strong>{employee.display_name}</strong></div>
                  <span className="employee-username">{employee.username}</span>
                  <span className="employee-type">{employee.employee_type === "kitchen" ? "Kitchen" : "Reception"}</span>
                  <span className={`employee-status ${employee.is_active ? "enabled" : "disabled"}`}><i />{employee.is_active ? "Active" : "Disabled"}</span>
                  <div className="employee-actions"><button onClick={() => { setSelectedEmployee(employee); setModal("password"); }}>Reset password</button><button className={employee.is_active ? "disable-action" : ""} onClick={() => toggleEmployeeStatus(employee)}>{employee.is_active ? "Disable" : "Enable"}</button></div>
                </div>)}
                {employees.length === 0 && <div className="employee-empty">No employee accounts yet. Add an employee to let them sign in and take orders.</div>}
              </div>
            </div>
            <div className="admin-note"><Icon name="sparkle" size={17} /><span><strong>Admin access</strong> — Only administrators can create employees or change their access and passwords.</span></div>
          </section>
        ) : (
          <section className="pos-page">
            <div className="pos-heading">
              <div><div className="eyebrow">{user.role === "admin" ? "MANAGER VIEW · ORDER ENTRY" : "RESTAURANT SERVICE"}</div><h1>Welcome, {user.display_name}<span>.</span></h1><p>What can we get started for the table?</p></div>
              <button className="new-order-button" onClick={startNewOrder}><Icon name="plus" size={16} /> New order</button>
            </div>

            <div className="pos-layout">
              <div className="catalog">
                <div className="catalog-controls">
                  <div className="tabs">
                    <button className={`order-tab ${orderType === "Dine in" ? "selected" : ""}`} onClick={() => setOrderType("Dine in")}><span className="table-glyph">▦</span> Dine in</button>
                    <button className={`order-tab ${orderType === "Takeaway" ? "selected" : ""}`} onClick={() => setOrderType("Takeaway")}><span className="takeaway-glyph">▤</span> Takeaway</button>
                  </div>
                  {orderType === "Dine in" ? <label className="table-select"><span>Table</span><select aria-label="Select table number" value={table} onChange={(event) => setTable(event.target.value)}>{Array.from({ length: 30 }, (_, index) => `Table ${String(index + 1).padStart(2, "0")}`).map((tableName) => <option key={tableName} value={tableName}>{tableName.replace("Table ", "")}</option>)}</select><Icon name="chevron" size={15} /></label> : <div className="table-select"><span>Pickup order</span></div>}
                </div>
                <div className="meal-tabs" role="group" aria-label="Choose meal service">
                  {mealServices.map((service) => <button
                    key={service.id}
                    className={`meal-option ${meal === service.id ? "selected" : ""}`}
                    aria-pressed={meal === service.id}
                    onClick={() => { setMeal(service.id); setCategory("All items"); }}
                  >
                    <span><strong>{service.name}</strong><small>{service.time}</small></span>
                    <i className="live-dot" />
                  </button>)}
                </div>
                <div className="catalog-toolbar">
                  <div className="category-tabs">{categoriesByMeal[meal].map((item) => <button key={item} className={category === item ? "current" : ""} onClick={() => setCategory(item)}>{item}</button>)}</div>
                  <label className="search-box"><Icon name="search" size={17} /><input ref={searchInputRef} value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search menu..." /><kbd>Ctrl/⌘ K</kbd></label>
                </div>
                <div className="catalog-meta"><span>Showing <strong>{visibleItems.length} items</strong></span><button onClick={() => setCategory("All items")}>View all <Icon name="arrow" size={14} /></button></div>
                <div className="product-grid">
                  {visibleItems.map((item) => <button className="product-card" key={item.id} onClick={() => addToCart(item)}>
                    <div className="product-image-wrap"><img className="product-image" src={imageUrl(item.image)} alt={item.name} /><span className="add-product"><Icon name="plus" size={18} /></span>{item.popular && <span className="popular-tag"><Icon name="sparkle" size={11} /> Popular</span>}</div>
                    <div className="product-details"><div className="product-name">{item.name}</div><div className="product-description">{item.description}</div><div className="product-price">{money(item.price)}</div></div>
                  </button>)}
                  {visibleItems.length === 0 && <div className="no-results">No menu items match “{search}”.</div>}
                </div>
                <div className="catalog-footer"><span><span className="live-dot" /> Menu is up to date</span><span>Prices shown in INR</span></div>
              </div>

              <aside className="order-panel">
                <div className="order-panel-head"><div><div className="order-title-row"><h2>Current order</h2><span className="order-number">{orderNumber ? `#${orderNumber}` : "NEW"}</span></div><div className="order-subtitle">{orderType} <span>·</span> {orderType === "Dine in" ? table : "Pickup"}</div></div><span className="more-button" aria-hidden="true">•••</span></div>
                <div className="guest-row"><div className="guest-icon"><Icon name="users" size={16} /></div><div><strong>{guestName || "Walk-in guest"}</strong><span>Guest details <span className="optional">· optional</span></span></div><button onClick={() => setModal("guest")}>Add</button></div>
                <div className="order-items-head"><span>ORDER ITEMS</span><span>{cart.reduce((sum, line) => sum + line.quantity, 0)} ITEMS</span></div>
                <div className={`order-lines ${cart.length ? "has-items" : ""}`}>
                  {cart.length === 0 ? <div className="empty-cart"><div className="empty-cart-icon"><Icon name="receiptSmall" size={23} /></div><strong>Your order is looking a little empty</strong><span>Tap any dish to add it here.</span></div> :
                    cart.map((line) => <div className="cart-line" key={line.id}><img src={imageUrl(line.image)} alt="" /><div className="cart-item-copy"><strong>{line.name}</strong><span>{money(line.price)} each</span><div className="quantity-control"><button onClick={() => updateQuantity(line.id, -1)} aria-label={`Remove one ${line.name}`}><Icon name="minus" size={12} /></button><span>{line.quantity}</span><button onClick={() => updateQuantity(line.id, 1)} aria-label={`Add one ${line.name}`}><Icon name="plus" size={12} /></button></div></div><strong className="line-total">{money(line.price * line.quantity)}</strong></div>)}
                </div>
                <button className="add-note" onClick={() => setModal("note")}><Icon name="edit" size={15} /> {orderNote ? "Edit order note" : "Add a note to this order"}</button>
                <div className="bill-details">
                  <div><span>Subtotal</span><span>{money(subtotal)}</span></div>
                  <div><span>GST <small>5%</small></span><span>{money(tax)}</span></div>
                  <div className="bill-total"><strong>Total due</strong><strong>{money(total)}</strong></div>
                </div>
                <div className="payment-section">
                  <div className="payment-label"><span>Cash received</span><button onClick={() => setCash(String(total))}>Exact amount</button></div>
                  <label className="cash-input"><span>₹</span><input aria-label="Cash received" type="number" min="0" value={cash} onChange={(event) => setCash(event.target.value)} placeholder="Enter amount received" /></label>
                  {Number(cash) > 0 && <div className={`change-row ${Number(cash) < total ? "short" : ""}`}><span>{Number(cash) < total ? "Amount remaining" : "Change to return"}</span><strong>{money(Math.abs(Number(cash) - total))}</strong></div>}
                </div>
                <button className="checkout-button" disabled={!cart.length || Number(cash) < total} onClick={completeOrder}>
                  <span>{cart.length && Number(cash) >= total ? "Place order" : "Collect payment"}</span><span>{money(total)} <Icon name="arrow" size={16} /></span>
                </button>
                <div className="secure-note"><Icon name="check" size={13} /> Order total includes GST</div>
              </aside>
            </div>
          </section>
        )}
      </main>
      {notice && <div className={`toast ${notice.startsWith("Could not") ? "error" : ""}`}><span className="toast-check"><Icon name={notice.startsWith("Could not") ? "close" : "check"} size={15} /></span><div><strong>{notice}</strong><span>{notice.startsWith("Could not") ? "No changes were saved. Please try again." : "Saved to the restaurant database."}</span></div><button onClick={() => setNotice("")}><Icon name="close" size={16} /></button></div>}
      {modal === "item" && <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) { setModal(null); setEditing(null); } }}><form className="modal-card" onSubmit={saveMenuItem}>
        <div className="modal-header"><div><div className="eyebrow">{editing ? "UPDATE YOUR MENU" : "GROW YOUR MENU"}</div><h2>{editing ? "Edit menu item" : "Add a menu item"}</h2></div><button type="button" className="modal-close" onClick={() => { setModal(null); setEditing(null); }}><Icon name="close" /></button></div>
        <label className="form-field">Item name<input name="name" required defaultValue={editing?.name ?? ""} placeholder="e.g. Paneer Butter Masala" /></label>
        <label className="form-field">Short description<input name="description" defaultValue={editing?.description ?? ""} placeholder="A little something about this dish" /></label>
        <div className="form-split"><label className="form-field">Category<select name="category" defaultValue={editing?.category ?? "Main course"}>{menuCategories.map((option) => <option key={option}>{option}</option>)}</select></label><label className="form-field">Selling price (₹)<input name="price" type="number" min="1" step="1" required defaultValue={editing?.price ?? ""} placeholder="0" /></label></div>
        <label className="form-field">Item cost (₹) — for daily profit<input name="cost_price" type="number" min="0" step="1" defaultValue={editing?.cost_price ?? ""} placeholder="Enter ingredient cost, or leave blank" /></label>
        <label className="form-field">Ingredients<input name="ingredients_text" maxLength="1000" defaultValue={editing?.ingredients_text ?? ""} placeholder="Only list confirmed ingredients" /></label>
        <label className="form-field">Allergens<input name="allergens_text" maxLength="500" defaultValue={editing?.allergens_text ?? ""} placeholder="Only list confirmed allergens" /></label>
        <fieldset className="dietary-editor"><legend>Dietary tags</legend>{["vegetarian", "non-vegetarian", "vegan", "gluten-free", "dairy-free"].map((tag) => <label key={tag}><input type="checkbox" name="dietary_tags" value={tag} defaultChecked={editing?.dietary_tags?.includes(tag) ?? false} />{tag}</label>)}</fieldset>
        <label className="verified-field"><input type="checkbox" name="dietary_verified" defaultChecked={editing?.dietary_verified ?? false} /> I verified these ingredients, allergens, and dietary tags</label>
        <div className="form-split"><label className="form-field">Spice level (0–5)<input name="spice_level" type="number" min="0" max="5" defaultValue={editing?.spice_level ?? ""} /></label><label className="form-field">Calories<input name="calories" type="number" min="0" max="5000" defaultValue={editing?.calories ?? ""} /></label></div>
        <div className="modal-actions"><button type="button" className="cancel-button" onClick={() => { setModal(null); setEditing(null); }}>Cancel</button><button type="submit" className="primary-button">{editing ? "Save changes" : "Add to menu"} <Icon name="arrow" size={15} /></button></div>
      </form></div>}
      {paymentPromptItem && <div className="modal-backdrop" role="presentation"><section className="modal-card compact-modal payment-confirmation" role="dialog" aria-modal="true" aria-labelledby="payment-confirmation-title">
        <div className="modal-header"><div><div className="eyebrow">ORDER READY</div><h2 id="payment-confirmation-title">Has the customer paid?</h2></div><button type="button" className="modal-close" onClick={() => setPaymentPromptItem(null)} aria-label="Close"><Icon name="close" /></button></div>
        <p>Order #{paymentPromptItem.order_id} total: <strong>{money(paymentPromptItem.order_total)}</strong>. Choose “Paid” only after receiving the full bill amount. This records exact payment with no change due.</p>
        <div className="payment-confirmation-actions"><button type="button" className="cancel-button" onClick={() => confirmOrderPayment(false)}>No, still unpaid</button><button type="button" className="primary-button" onClick={() => confirmOrderPayment(true)}>Yes, paid in full</button></div>
      </section></div>}
      {(modal === "guest" || modal === "note") && <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setModal(null); }}><form className="modal-card compact-modal" onSubmit={(event) => { event.preventDefault(); const data = new FormData(event.currentTarget); if (modal === "guest") setGuestName(String(data.get("guest_name") || "").trim()); else setOrderNote(String(data.get("note") || "").trim()); setModal(null); }}>
        <div className="modal-header"><div><div className="eyebrow">{orderNumber ? `ORDER #${orderNumber}` : "NEW ORDER"}</div><h2>{modal === "guest" ? "Guest details" : "Order note"}</h2></div><button type="button" className="modal-close" onClick={() => setModal(null)}><Icon name="close" /></button></div>
        {modal === "guest" ? <label className="form-field">Guest name<input name="guest_name" defaultValue={guestName} placeholder="Name (optional)" /></label> : <label className="form-field">Kitchen note<textarea name="note" defaultValue={orderNote} placeholder="e.g. Less spicy, no onions..." rows="3" /></label>}
        <div className="modal-actions"><button type="button" className="cancel-button" onClick={() => setModal(null)}>Cancel</button><button type="submit" className="primary-button">Save details <Icon name="arrow" size={15} /></button></div>
      </form></div>}
      {(modal === "employee" || modal === "password") && <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) { setModal(null); setSelectedEmployee(null); } }}><form className="modal-card compact-modal" onSubmit={modal === "employee" ? saveEmployee : saveEmployeePassword}>
        <div className="modal-header"><div><div className="eyebrow">ADMINISTRATOR ONLY</div><h2>{modal === "employee" ? "Add an employee" : "Reset employee password"}</h2></div><button type="button" className="modal-close" onClick={() => { setModal(null); setSelectedEmployee(null); }}><Icon name="close" /></button></div>
        {modal === "employee" ? <><label className="form-field">Full name<input name="display_name" required maxLength="120" placeholder="e.g. Neha Patel" /></label><label className="form-field">Username<input name="username" required minLength="3" maxLength="80" pattern="[a-zA-Z0-9._-]+" placeholder="e.g. neha.patel" /></label><label className="form-field">Work area<select name="employee_type" defaultValue="reception"><option value="reception">Reception — take orders and track kitchen progress</option><option value="kitchen">Kitchen — prepare orders and update checklist</option></select></label><label className="form-field">Temporary password<input name="password" type="password" required minLength="8" maxLength="256" autoComplete="new-password" placeholder="At least 8 characters" /></label></> : <><p className="employee-password-copy">Set a new password for <strong>{selectedEmployee?.display_name}</strong>. Give the new password directly to this employee.</p><label className="form-field">New password<input name="password" type="password" required minLength="8" maxLength="256" autoComplete="new-password" placeholder="At least 8 characters" /></label></>}
        <div className="modal-actions"><button type="button" className="cancel-button" onClick={() => { setModal(null); setSelectedEmployee(null); }}>Cancel</button><button type="submit" className="primary-button">{modal === "employee" ? "Create account" : "Reset password"} <Icon name="arrow" size={15} /></button></div>
      </form></div>}
    </div>
  );
}

export default function App() {
  if (window.location.pathname === "/order") return <CustomerPortal />;
  return <StaffApp />;
}
