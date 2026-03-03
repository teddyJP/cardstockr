import React, { useEffect, useState } from "react";

type CardSearchResult = {
  card_id: string;
  name: string;
  set_name: string;
  year: number;
  number: string;
  variant?: string | null;
  set_slug?: string | null;
  image_url?: string | null;
  grade_company?: string;
  grade_value?: number;
  raw_median_usd?: number | null;
   raw_low_usd?: number | null;
   raw_high_usd?: number | null;
  raw_sales_count?: number;
};

type PriceByGrade = {
  label: string;
  grade_company: string | null;
  grade_value: number | null;
  median_price_usd: number;
  count: number;
};

type CompanyGradeDistribution = {
  company: string;
  total_graded: number;
  by_grade: { grade_value: number; count: number }[];
  ten_rate: number | null;
};

type GradingUpside = {
  raw_median_usd: number;
  grading_cost_usd: number;
  by_company: { company: string; ev_usd: number; upside_usd: number; worth_grading: boolean }[];
  worth_grading_any: boolean;
};

type RawConditionBucket = {
  median_price_usd: number;
  count: number;
};

type CompanyPriceBand = {
  company: string;
  low_usd: number | null;
  median_usd: number | null;
  high_usd: number | null;
  sales_count: number;
};

type CardDetail = {
  card_id: string;
  name: string;
  set_name: string;
  year: number;
  number: string;
  grade_company?: string;
  grade_value?: number;
  canonical_card_id?: string | null;
  set_slug?: string | null;
  card_slug?: string | null;
  image_url?: string | null;
  fair_value_now: number;
  fair_value_ci_low: number;
  fair_value_ci_high: number;
  forecast_horizon_days: number;
  liquidity_score: number;
  risk_score: number;
  change_30d_pct?: number | null;
  change_90d_pct?: number | null;
  raw_low_usd?: number | null;
  raw_median_usd?: number | null;
  raw_high_usd?: number | null;
  raw_sales_count?: number;
  recent_window_days?: number;
  prices_by_grade?: PriceByGrade[];
  grade_distribution?: CompanyGradeDistribution[];
  grading_upside?: GradingUpside | null;
  graded_price_bands?: CompanyPriceBand[];
  raw_by_condition?: Record<string, RawConditionBucket>;
  recent_raw_by_condition?: Record<string, RawConditionBucket>;
  recent_prices_by_grade?: PriceByGrade[];
  history?: { date: string; median_price: number; sales_count: number }[];
  forecast?: { date: string; p10: number; p50: number; p90: number }[];
};

type CardSeriesPoint = { date: string; median_price_usd: number; sales_count: number };
type CardSeriesLine = { label: string; grade_company: string | null; points: CardSeriesPoint[] };
type CardSeriesResponse = {
  canonical_card_id: string | null;
  group_by: "company" | "combined";
  companies: string[];
  grades: number[];
  include_raw: boolean;
  series: CardSeriesLine[];
};

type MetricsSummary = {
  total_sales: number;
  by_language: Record<string, number>;
  raw_count: number;
  graded_count: number;
};

type GradeBucket = { grade_label: string; count: number; median_price_usd: number | null };
type ByGradeResponse = { buckets: GradeBucket[]; language_filter: string | null };

type CompanyGradeBucket = { grade_value: number | null; count: number; median_price_usd: number | null };
type CompanyBucket = {
  company: string;
  count: number;
  median_price_usd: number | null;
  grade_breakdown: CompanyGradeBucket[];
};
type ByCompanyResponse = { buckets: CompanyBucket[]; language_filter: string | null };

type TenRateResponse = {
  overall_ten_rate: number | null;
  graded_count: number;
  ten_count: number;
  by_company: Record<string, number>;
};

type MoverCard = {
  card_id: string;
  name: string;
  set_slug: string | null;
  set_name: string | null;
  window_days: number;
  value_now_usd: number | null;
  value_prev_usd: number | null;
  change_pct: number | null;
  sales_now: number;
  sales_prev: number;
};

type MoversResponse = {
  window_days: number;
  min_sales_now: number;
  min_sales_prev: number;
  cards: MoverCard[];
};

type SetSummary = { set_slug: string; set_name: string; game: string | null; card_count: number };
type CardInSet = {
  card_id: string;
  card_slug: string;
  name: string;
  set_name: string | null;
  number: string | null;
  image_url?: string | null;
  variant?: string | null;
};
type SetTopCard = { card_id: string; name: string; value_usd: number; change_pct: number | null; sales_per_week: number | null };
type SetAnalytics = {
  set_slug: string;
  set_name: string;
  total_sales: number;
  raw_sales: number;
  graded_sales: number;
  language_filter: string | null;
  top_movers_30d: SetTopCard[];
  top_movers_90d: SetTopCard[];
  top_liquidity: SetTopCard[];
  index_history: { date: string; median_price: number; sales_count: number }[];
};

type GradingTarget = {
  card_id: string;
  name: string;
  set_slug: string | null;
  card_slug: string | null;
  raw_count: number;
  raw_median_usd: number;
  graded_count: number;
  best_company: string | null;
  best_ev_usd: number | null;
  best_upside_usd: number | null;
  sales_per_week: number;
  volatility: number | null;
};

type GradingTargetsResponse = {
  grading_cost_usd: number;
  language_filter: string | null;
  set_slug_filter: string | null;
  min_raw_sales: number;
  min_graded_sales: number;
  limit: number;
  targets: GradingTarget[];
};

export const App: React.FC = () => {
  const [view, setView] = useState<"cards" | "metrics" | "sets" | "targets" | "movers">("cards");
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<CardSearchResult[]>([]);
  const [selected, setSelected] = useState<CardDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [metricsSummary, setMetricsSummary] = useState<MetricsSummary | null>(null);
  const [byGrade, setByGrade] = useState<ByGradeResponse | null>(null);
  const [byCompany, setByCompany] = useState<ByCompanyResponse | null>(null);
  const [tenRate, setTenRate] = useState<TenRateResponse | null>(null);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [metricsError, setMetricsError] = useState<string | null>(null);
  const [metricsLang, setMetricsLang] = useState<string>("");
  const [setSearchQuery, setSetSearchQuery] = useState("");
  const [setsList, setSetsList] = useState<SetSummary[]>([]);
  const [selectedSetSlug, setSelectedSetSlug] = useState<string | null>(null);
  const [cardsInSet, setCardsInSet] = useState<CardInSet[]>([]);
  const [setsLoading, setSetsLoading] = useState(false);
  const [setsError, setSetsError] = useState<string | null>(null);
  const [setsLang, setSetsLang] = useState<string>("");
   const [setCardsFilter, setSetCardsFilter] = useState<string>("");
  const [setAnalytics, setSetAnalytics] = useState<SetAnalytics | null>(null);
  const [setTargetsPreview, setSetTargetsPreview] = useState<GradingTarget[]>([]);

  const [gradingPurchasePriceUsd, setGradingPurchasePriceUsd] = useState<number | null>(null);
  const [gradingDefaultCostUsd, setGradingDefaultCostUsd] = useState<number>(25);
  const [gradingCostByCompany, setGradingCostByCompany] = useState<Record<string, number>>({});
  const [selectedCondition, setSelectedCondition] = useState<string | null>(null);

  const [cardSeries, setCardSeries] = useState<CardSeriesResponse | null>(null);
  const [seriesCompanies, setSeriesCompanies] = useState<Record<string, boolean>>({});
  const [seriesGrades, setSeriesGrades] = useState<Record<string, boolean>>({});
  const [seriesIncludeRaw, setSeriesIncludeRaw] = useState(true);
  const [seriesRawConditions, setSeriesRawConditions] = useState<Record<string, boolean>>({});
  const [seriesLoading, setSeriesLoading] = useState(false);
  const [seriesError, setSeriesError] = useState<string | null>(null);

  const [rawConditionSort, setRawConditionSort] = useState<"condition" | "median" | "count">("condition");
  const [cardImageError, setCardImageError] = useState(false);
  const [cardImageLoaded, setCardImageLoaded] = useState(false);

  const [cardsLang, setCardsLang] = useState<string>("");
  const [targetsLang, setTargetsLang] = useState<string>("");
  const [targetsSetSlug, setTargetsSetSlug] = useState<string>("");
  const [targetsMinRaw, setTargetsMinRaw] = useState<number>(2);
  const [targetsMinGraded, setTargetsMinGraded] = useState<number>(2);
  const [targetsLimit, setTargetsLimit] = useState<number>(50);
  const [targetsDefaultCost, setTargetsDefaultCost] = useState<number>(25);
  const [targetsMinSalesPerWeek, setTargetsMinSalesPerWeek] = useState<number>(0);
  const [targetsMaxVolatility, setTargetsMaxVolatility] = useState<number | null>(null);
  const [targetsMinUpside, setTargetsMinUpside] = useState<number | null>(null);
  const [targetsLoading, setTargetsLoading] = useState(false);
  const [targetsError, setTargetsError] = useState<string | null>(null);
  const [targetsData, setTargetsData] = useState<GradingTargetsResponse | null>(null);

  const [moversWindow, setMoversWindow] = useState<number>(30);
  const [moversMinNow, setMoversMinNow] = useState<number>(3);
  const [moversMinPrev, setMoversMinPrev] = useState<number>(3);
  const [moversLoading, setMoversLoading] = useState(false);
  const [moversError, setMoversError] = useState<string | null>(null);
  const [moversData, setMoversData] = useState<MoversResponse | null>(null);
  const [moversLang, setMoversLang] = useState<string>("");
  const [historyRange, setHistoryRange] = useState<"30d" | "90d" | "1y" | "all">("all");

  useEffect(() => {
    if (typeof window === "undefined") return;
    const stored = window.localStorage.getItem("tcg-theme");
    if (stored === "light" || stored === "dark") {
      setTheme(stored);
    }
  }, []);

  useEffect(() => {
    if (typeof document === "undefined") return;
    const cls = theme === "light" ? "theme-light" : "";
    document.body.className = cls;
    if (typeof window !== "undefined") {
      window.localStorage.setItem("tcg-theme", theme);
    }
  }, [theme]);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setSelected(null);

    try {
      const params = new URLSearchParams();
      params.set("q", query);
      if (cardsLang) params.set("language", cardsLang);
      const res = await fetch(`/api/v1/cards/search?${params.toString()}`);
      if (!res.ok) {
        throw new Error(`Search failed with status ${res.status}`);
      }
      const data: CardSearchResult[] = await res.json();
      setResults(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function loadMetrics() {
    setMetricsLoading(true);
    setMetricsError(null);
    const langQ = metricsLang ? `?language=${encodeURIComponent(metricsLang)}` : "";
    try {
      const [s, g, c, t] = await Promise.all([
        fetch("/api/v1/metrics/summary").then((r) => (r.ok ? r.json() : null)),
        fetch(`/api/v1/metrics/by-grade${langQ}`).then((r) => (r.ok ? r.json() : null)),
        fetch(`/api/v1/metrics/by-company${langQ}`).then((r) => (r.ok ? r.json() : null)),
        fetch(`/api/v1/metrics/ten-rate${langQ}`).then((r) => (r.ok ? r.json() : null)),
      ]);
      setMetricsSummary(s);
      setByGrade(g);
      setByCompany(c);
      setTenRate(t);
    } catch (err) {
      setMetricsError((err as Error).message);
    } finally {
      setMetricsLoading(false);
    }
  }

  useEffect(() => {
    if (view === "metrics") loadMetrics();
  }, [view, metricsLang]);

  async function loadMovers() {
    setMoversLoading(true);
    setMoversError(null);
    try {
      const params = new URLSearchParams();
      params.set("window_days", String(moversWindow));
      params.set("min_sales_now", String(moversMinNow));
      params.set("min_sales_prev", String(moversMinPrev));
      params.set("limit", "100");
      if (moversLang) params.set("language", moversLang);
      const res = await fetch(`/api/v1/metrics/movers?${params.toString()}`);
      if (!res.ok) throw new Error(`Movers failed: ${res.status}`);
      const data: MoversResponse = await res.json();
      setMoversData(data);
    } catch (err) {
      setMoversError((err as Error).message);
    } finally {
      setMoversLoading(false);
    }
  }

  useEffect(() => {
    if (view === "movers" && !moversData) loadMovers();
  }, [view]);

  useEffect(() => {
    if (view === "sets" && setsList.length === 0) loadSets();
  }, [view]);

  async function loadTargets() {
    setTargetsLoading(true);
    setTargetsError(null);
    try {
      const params = new URLSearchParams();
      params.set("limit", String(targetsLimit));
      params.set("grading_cost_usd", String(targetsDefaultCost));
      params.set("min_raw_sales", String(targetsMinRaw));
      params.set("min_graded_sales", String(targetsMinGraded));
      params.set("min_sales_per_week", String(targetsMinSalesPerWeek));
      if (targetsMaxVolatility != null) params.set("max_volatility", String(targetsMaxVolatility));
      if (targetsMinUpside != null) params.set("min_upside_usd", String(targetsMinUpside));
      if (targetsLang) params.set("language", targetsLang);
      if (targetsSetSlug) params.set("set_slug", targetsSetSlug);
      const res = await fetch(`/api/v1/targets/grading?${params.toString()}`);
      if (!res.ok) throw new Error(`Targets failed: ${res.status}`);
      const data: GradingTargetsResponse = await res.json();
      setTargetsData(data);
    } catch (err) {
      setTargetsError((err as Error).message);
    } finally {
      setTargetsLoading(false);
    }
  }

  useEffect(() => {
    if (view === "targets" && !targetsData) loadTargets();
  }, [view]);

  // Simple hash-based deep linking for sets: #set={set_slug}
  useEffect(() => {
    if (typeof window === "undefined") return;
    const hash = window.location.hash || "";
    if (hash.startsWith("#set=")) {
      const slug = decodeURIComponent(hash.slice(5));
      if (slug) {
        setView("sets");
        loadCardsInSet(slug);
      }
    }
  }, []);

  async function loadCard(cardId: string, switchToCardsView = false) {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/cards/${encodeURIComponent(cardId)}`);
      if (!res.ok) {
        throw new Error(`Card fetch failed with status ${res.status}`);
      }
      const data: CardDetail = await res.json();
      setSelected(data);
      // Initialize grading inputs from the selected card
      const rawRow = data.prices_by_grade?.find((p) => p.label === "Ungraded");
      const rawMedian = rawRow?.median_price_usd ?? data.grading_upside?.raw_median_usd ?? null;

      const condBuckets = data.raw_by_condition ?? {};
      const conditionKeys = Object.keys(condBuckets);
      // Prefer NM, then LP, else first available bucket.
      let initialCondition: string | null = null;
      if (conditionKeys.includes("NM")) initialCondition = "NM";
      else if (conditionKeys.includes("LP")) initialCondition = "LP";
      else if (conditionKeys.length > 0) initialCondition = conditionKeys[0];
      setSelectedCondition(initialCondition);

      const conditionMedian =
        initialCondition && condBuckets[initialCondition]
          ? condBuckets[initialCondition].median_price_usd
          : null;

      setGradingPurchasePriceUsd(conditionMedian ?? rawMedian);
      setGradingDefaultCostUsd(data.grading_upside?.grading_cost_usd ?? 25);
      setGradingCostByCompany({});
      // Initialize series toggles from available buckets
      const comps = Array.from(new Set((data.prices_by_grade ?? []).filter((p) => p.grade_company).map((p) => p.grade_company as string))).sort();
      const grades = Array.from(new Set((data.prices_by_grade ?? []).filter((p) => p.grade_value != null && p.grade_company).map((p) => String(p.grade_value)))).sort((a, b) => Number(b) - Number(a));
      const compState: Record<string, boolean> = {};
      for (const c of comps) compState[c] = true;
      setSeriesCompanies(compState);
      const gradeState: Record<string, boolean> = {};
      for (const g of grades.slice(0, 6)) gradeState[g] = true; // default: top grades
      setSeriesGrades(gradeState);
      setSeriesIncludeRaw(true);
      const rawCondKeys = Object.keys(data.raw_by_condition ?? {});
      const rawCondState: Record<string, boolean> = {};
      for (const c of rawCondKeys) {
        rawCondState[c] = c === "NM" || c === "LP";
      }
      setSeriesRawConditions(rawCondState);
      setCardSeries(null);
      setCardImageError(false);
      setCardImageLoaded(false);
      if (switchToCardsView) setView("cards");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function loadFilteredSeries(detail: CardDetail) {
    setSeriesLoading(true);
    setSeriesError(null);
    try {
      const companies = Object.entries(seriesCompanies).filter(([, v]) => v).map(([k]) => k);
      const grades = Object.entries(seriesGrades).filter(([, v]) => v).map(([k]) => k);
      const rawConds = Object.entries(seriesRawConditions).filter(([, v]) => v).map(([k]) => k);
      const params = new URLSearchParams();
      params.set("card_id", detail.card_id);
      if (companies.length) params.set("companies", companies.join(","));
      if (grades.length) params.set("grades", grades.join(","));
      params.set("include_raw", String(seriesIncludeRaw));
      if (seriesIncludeRaw && rawConds.length > 0) params.set("raw_conditions", rawConds.join(","));
      params.set("group_by", "company");
      const res = await fetch(`/api/v1/cards/series?${params.toString()}`);
      if (!res.ok) throw new Error(`Series failed: ${res.status}`);
      const data: CardSeriesResponse = await res.json();
      setCardSeries(data);
    } catch (err) {
      setSeriesError((err as Error).message);
    } finally {
      setSeriesLoading(false);
    }
  }

  async function loadSets() {
    setSetsLoading(true);
    setSetsError(null);
    try {
      const q = setSearchQuery ? `?q=${encodeURIComponent(setSearchQuery)}` : "";
      const res = await fetch(`/api/v1/sets${q}`);
      if (!res.ok) throw new Error(`Sets failed: ${res.status}`);
      const data: SetSummary[] = await res.json();
      setSetsList(data);
      setSelectedSetSlug(null);
      setCardsInSet([]);
    } catch (err) {
      setSetsError((err as Error).message);
    } finally {
      setSetsLoading(false);
    }
  }

  async function loadCardsInSet(setSlug: string) {
    setSelectedSetSlug(setSlug);
    setSetsLoading(true);
    setSetsError(null);
    try {
      const langParam = setsLang ? `?language=${encodeURIComponent(setsLang)}` : "";
      const [cardsRes, analyticsRes, targetsRes] = await Promise.all([
        fetch(`/api/v1/sets/${encodeURIComponent(setSlug)}/cards`),
        fetch(`/api/v1/sets/${encodeURIComponent(setSlug)}/analytics${langParam}`),
        fetch(
          `/api/v1/targets/grading?set_slug=${encodeURIComponent(setSlug)}&limit=10&min_raw_sales=2&min_graded_sales=2${
            setsLang ? `&language=${encodeURIComponent(setsLang)}` : ""
          }`,
        ),
      ]);

      if (!cardsRes.ok) throw new Error(`Cards in set failed: ${cardsRes.status}`);
      const cardsData: CardInSet[] = await cardsRes.json();
      setCardsInSet(cardsData);

      if (analyticsRes.ok) {
        const a: SetAnalytics = await analyticsRes.json();
        setSetAnalytics(a);
      } else {
        setSetAnalytics(null);
      }

      if (targetsRes.ok) {
        const t: GradingTargetsResponse = await targetsRes.json();
        setSetTargetsPreview(t.targets ?? []);
      } else {
        setSetTargetsPreview([]);
      }
    } catch (err) {
      setSetsError((err as Error).message);
    } finally {
      setSetsLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-row">
          <div>
            <h1>TCG Market Predictor</h1>
            <p className="subtitle">Pokémon – MVP</p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <div className="theme-toggle">
              <span>{theme === "dark" ? "Dark" : "Light"} mode</span>
              <button
                type="button"
                onClick={() => setTheme((prev) => (prev === "dark" ? "light" : "dark"))}
              >
                {theme === "dark" ? "Switch to light" : "Switch to dark"}
              </button>
            </div>
            <nav className="header-nav">
            <button
              type="button"
              className={view === "cards" ? "active" : ""}
              onClick={() => setView("cards")}
            >
              Cards
            </button>
            <button
              type="button"
              className={view === "sets" ? "active" : ""}
              onClick={() => setView("sets")}
            >
              Sets
            </button>
            <button
              type="button"
              className={view === "targets" ? "active" : ""}
              onClick={() => setView("targets")}
            >
              Targets
            </button>
            <button
              type="button"
              className={view === "metrics" ? "active" : ""}
              onClick={() => setView("metrics")}
            >
              Market metrics
            </button>
            <button
              type="button"
              className={view === "movers" ? "active" : ""}
              onClick={() => setView("movers")}
            >
              Big movers
            </button>
          </nav>
          </div>
        </div>
      </header>

      {view === "targets" ? (
        <main className="main metrics-main">
          <section className="metrics-section">
            <h2>Grading targets</h2>
            <div className="metrics-filters">
              <label>
                Language{" "}
                <select value={targetsLang} onChange={(e) => { setTargetsLang(e.target.value); setTargetsData(null); }}>
                  <option value="">All</option>
                  <option value="en">English</option>
                  <option value="jp">Japanese</option>
                  <option value="other">Other</option>
                </select>
              </label>
              <input
                type="text"
                placeholder="set_slug filter (optional)"
                value={targetsSetSlug}
                onChange={(e) => { setTargetsSetSlug(e.target.value); setTargetsData(null); }}
              />
              <input
                className="small-input"
                type="number"
                value={targetsMinSalesPerWeek}
                onChange={(e) => { setTargetsMinSalesPerWeek(Number(e.target.value) || 0); setTargetsData(null); }}
                placeholder="min sales/wk"
              />
              <input
                className="small-input"
                type="number"
                value={targetsMaxVolatility ?? ""}
                onChange={(e) => { setTargetsMaxVolatility(e.target.value ? Number(e.target.value) : null); setTargetsData(null); }}
                placeholder="max vol"
              />
              <input
                className="small-input"
                type="number"
                value={targetsMinUpside ?? ""}
                onChange={(e) => { setTargetsMinUpside(e.target.value ? Number(e.target.value) : null); setTargetsData(null); }}
                placeholder="min upside"
              />
              <input
                className="small-input"
                type="number"
                value={targetsDefaultCost}
                onChange={(e) => { setTargetsDefaultCost(Number(e.target.value) || 0); setTargetsData(null); }}
                placeholder="grading cost"
              />
              <button type="button" onClick={loadTargets} disabled={targetsLoading}>
                {targetsLoading ? "Loading…" : "Refresh"}
              </button>
            </div>
            {targetsError && <p className="error">{targetsError}</p>}
            {targetsData && (
              <div className="card-block">
                <div className="set-cards-header">
                  <p className="muted" style={{ margin: 0 }}>
                    Ranked by best upside (EV − raw − cost), then liquidity. Cost=${targetsData.grading_cost_usd}. Click a row to open that card.
                  </p>
                  <button
                    type="button"
                    onClick={() => {
                      const headers = ["card_id", "name", "set_slug", "raw_median_usd", "best_company", "best_ev_usd", "best_upside_usd", "sales_per_week", "volatility", "raw_count", "graded_count"];
                      const rows = targetsData.targets.map((t) => [
                        t.card_id,
                        t.name,
                        t.set_slug ?? "",
                        t.raw_median_usd,
                        t.best_company ?? "",
                        t.best_ev_usd ?? "",
                        t.best_upside_usd ?? "",
                        t.sales_per_week,
                        t.volatility ?? "",
                        t.raw_count,
                        t.graded_count,
                      ]);
                      const csv = [headers.join(","), ...rows.map((r) => r.map((c) => (typeof c === "string" && (c.includes(",") || c.includes('"')) ? `"${c.replace(/"/g, '""')}"` : c)).join(","))].join("\n");
                      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
                      const a = document.createElement("a");
                      a.href = URL.createObjectURL(blob);
                      a.download = `grading-targets-${new Date().toISOString().slice(0, 10)}.csv`;
                      a.click();
                      URL.revokeObjectURL(a.href);
                    }}
                  >
                    Export CSV
                  </button>
                </div>
                <table className="metrics-table">
                  <thead>
                    <tr>
                      <th>Card</th>
                      <th>Raw median</th>
                      <th>Best</th>
                      <th>EV</th>
                      <th>Upside</th>
                      <th>Sales/wk</th>
                      <th>Vol</th>
                      <th>Raw</th>
                      <th>Graded</th>
                    </tr>
                  </thead>
                  <tbody>
                    {targetsData.targets.map((t) => (
                      <tr key={t.card_id} className="clickable-row" onClick={() => loadCard(t.card_id, true)}>
                        <td>
                          <strong>{t.name}</strong>
                          {t.set_slug && <div className="muted">{t.set_slug}</div>}
                        </td>
                        <td>${t.raw_median_usd.toFixed(2)}</td>
                        <td>{t.best_company ?? "—"}</td>
                        <td>{t.best_ev_usd != null ? `$${t.best_ev_usd.toFixed(2)}` : "—"}</td>
                        <td className={t.best_upside_usd != null && t.best_upside_usd > 0 ? "pos" : "neg"}>
                          {t.best_upside_usd != null
                            ? t.best_upside_usd >= 0
                              ? `+$${t.best_upside_usd.toFixed(2)}`
                              : `-$${Math.abs(t.best_upside_usd).toFixed(2)}`
                            : "—"}
                        </td>
                        <td>{t.sales_per_week.toFixed(2)}</td>
                        <td>{t.volatility != null ? t.volatility.toFixed(4) : "—"}</td>
                        <td>{t.raw_count}</td>
                        <td>{t.graded_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </main>
      ) : view === "sets" ? (
        <main className="main metrics-main">
          <section className="metrics-section">
            <h2>Browse by set</h2>
            <div className="metrics-filters">
              <input
                type="text"
                placeholder="Search set name (e.g. Ascended Heroes)"
                value={setSearchQuery}
                onChange={(e) => setSetSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && loadSets()}
              />
              <button type="button" onClick={loadSets} disabled={setsLoading}>
                {setsLoading ? "Loading…" : "Search sets"}
              </button>
              <label>
                Language{" "}
                <select
                  value={setsLang}
                  onChange={(e) => {
                    const v = e.target.value;
                    setSetsLang(v);
                    if (selectedSetSlug) {
                      loadCardsInSet(selectedSetSlug);
                    }
                  }}
                >
                  <option value="">All</option>
                  <option value="en">English</option>
                  <option value="jp">Japanese</option>
                  <option value="other">Other</option>
                </select>
              </label>
            </div>
            {setsError && <p className="error">{setsError}</p>}
            {setsList.length > 0 && (
              <div className="card-block">
                <h3>Sets</h3>
                <ul className="results-list">
                  {setsList.map((s) => (
                    <li
                      key={s.set_slug}
                      onClick={() => {
                        if (typeof window !== "undefined") {
                          window.location.hash = `set=${encodeURIComponent(s.set_slug)}`;
                        }
                        loadCardsInSet(s.set_slug);
                      }}
                      className={selectedSetSlug === s.set_slug ? "selected" : ""}
                    >
                      <strong>{s.set_name}</strong> — {s.card_count} cards
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {selectedSetSlug && cardsInSet.length > 0 && (
              <div className="card-block">
                <div className="set-cards-header">
                  <h3>Cards in set</h3>
                  <button
                    type="button"
                    onClick={() => {
                      setTargetsSetSlug(selectedSetSlug);
                      setTargetsData(null);
                      setView("targets");
                    }}
                  >
                    Show targets for this set
                  </button>
                </div>

                <div className="metrics-filters" style={{ marginTop: "0.5rem" }}>
                  <input
                    type="text"
                    placeholder="Filter cards in this set..."
                    value={setCardsFilter}
                    onChange={(e) => setSetCardsFilter(e.target.value)}
                  />
                </div>

                {setAnalytics && (
                  <div className="set-panels">
                    {setAnalytics.index_history && setAnalytics.index_history.length > 1 && (
                      <div className="metrics-block">
                        <h3>Set index (daily median)</h3>
                        <LineChart
                          points={setAnalytics.index_history.map((p) => ({
                            x: p.date,
                            y: p.median_price,
                          }))}
                          height={160}
                        />
                      </div>
                    )}

                    <div className="metrics-summary-cards">
                      <div className="metric-card">
                        <h3>Total sales</h3>
                        <p className="metric-number">{setAnalytics.total_sales.toLocaleString()}</p>
                      </div>
                      <div className="metric-card">
                        <h3>Raw</h3>
                        <p className="metric-number">{setAnalytics.raw_sales.toLocaleString()}</p>
                      </div>
                      <div className="metric-card">
                        <h3>Graded</h3>
                        <p className="metric-number">{setAnalytics.graded_sales.toLocaleString()}</p>
                      </div>
                    </div>

                    {setAnalytics.top_movers_30d.length > 0 && (
                      <div className="metrics-block">
                        <h3>Top movers (30d)</h3>
                        <table className="metrics-table">
                          <thead>
                            <tr>
                              <th>Card</th>
                              <th>Median</th>
                              <th>Change</th>
                            </tr>
                          </thead>
                          <tbody>
                            {setAnalytics.top_movers_30d.map((m) => (
                              <tr key={m.card_id} className="clickable-row" onClick={() => loadCard(m.card_id, true)}>
                                <td><strong>{m.name}</strong></td>
                                <td>${m.value_usd.toFixed(2)}</td>
                                <td className={m.change_pct != null && m.change_pct > 0 ? "pos" : "neg"}>
                                  {m.change_pct != null ? `${(m.change_pct * 100).toFixed(1)}%` : "—"}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}

                    {setAnalytics.top_liquidity.length > 0 && (
                      <div className="metrics-block">
                        <h3>Top liquidity</h3>
                        <table className="metrics-table">
                          <thead>
                            <tr>
                              <th>Card</th>
                              <th>Median</th>
                              <th>Sales/wk</th>
                            </tr>
                          </thead>
                          <tbody>
                            {setAnalytics.top_liquidity.map((l) => (
                              <tr key={l.card_id} className="clickable-row" onClick={() => loadCard(l.card_id, true)}>
                                <td><strong>{l.name}</strong></td>
                                <td>${l.value_usd.toFixed(2)}</td>
                                <td>{(l.sales_per_week ?? 0).toFixed(2)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}

                    {setTargetsPreview.length > 0 && (
                      <div className="metrics-block">
                        <h3>Top grading targets (in set)</h3>
                        <table className="metrics-table">
                          <thead>
                            <tr>
                              <th>Card</th>
                              <th>Best</th>
                              <th>Upside</th>
                            </tr>
                          </thead>
                          <tbody>
                            {setTargetsPreview.map((t) => (
                              <tr key={t.card_id} className="clickable-row" onClick={() => loadCard(t.card_id, true)}>
                                <td><strong>{t.name}</strong></td>
                                <td>{t.best_company ?? "—"}</td>
                                <td className={t.best_upside_usd != null && t.best_upside_usd > 0 ? "pos" : "neg"}>
                                  {t.best_upside_usd != null ? `$${t.best_upside_usd.toFixed(2)}` : "—"}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}

                <ul className="results-list">
                  {cardsInSet
                    .filter((c) => {
                      const q = setCardsFilter.trim().toLowerCase();
                      if (!q) return true;
                      return (
                        c.name.toLowerCase().includes(q) ||
                        (c.card_slug && c.card_slug.toLowerCase().includes(q)) ||
                        (c.number && c.number.toLowerCase().includes(q))
                      );
                    })
                    .map((c) => (
                      <li key={c.card_id} onClick={() => loadCard(c.card_id, true)}>
                        <div className="result-row">
                          {c.image_url && (
                            <img
                              src={c.image_url}
                              alt={c.name}
                              className="result-thumb"
                              loading="lazy"
                            />
                          )}
                          <div>
                            <div className="result-title">
                              {c.name}
                              {c.variant && (
                                <span className="muted" style={{ marginLeft: "0.25rem", fontSize: "0.8rem" }}>
                                  · {c.variant}
                                </span>
                              )}
                            </div>
                            <div className="result-meta">
                              {c.set_name ?? ""}{c.number ? ` · #${c.number}` : ""}{" "}
                              <span className="muted">{c.card_slug}</span>
                            </div>
                          </div>
                        </div>
                      </li>
                    ))}
                </ul>
              </div>
            )}
            {view === "sets" && setsList.length === 0 && !setsLoading && (
              <p className="muted">Run the backfill script, then search sets (e.g. leave empty and click Search sets to load all).</p>
            )}
          </section>
        </main>
      ) : view === "metrics" ? (
        <main className="main metrics-main">
          <section className="metrics-section">
            <h2>Market metrics</h2>
            <div className="metrics-filters">
              <label>
                Language:{" "}
                <select
                  value={metricsLang}
                  onChange={(e) => {
                    setMetricsLang(e.target.value);
                    setMetricsSummary(null);
                  }}
                >
                  <option value="">All</option>
                  <option value="en">English</option>
                  <option value="jp">Japanese</option>
                  <option value="other">Other</option>
                </select>
              </label>
              <button type="button" onClick={loadMetrics} disabled={metricsLoading}>
                {metricsLoading ? "Loading…" : "Refresh"}
              </button>
            </div>
            {metricsError && <p className="error">{metricsError}</p>}
            {metricsSummary && (
              <>
                <div className="metrics-summary-cards">
                  <div className="metric-card">
                    <h3>Total sales</h3>
                    <p className="metric-number">{metricsSummary.total_sales.toLocaleString()}</p>
                  </div>
                  <div className="metric-card">
                    <h3>Raw</h3>
                    <p className="metric-number">{metricsSummary.raw_count.toLocaleString()}</p>
                  </div>
                  <div className="metric-card">
                    <h3>Graded</h3>
                    <p className="metric-number">{metricsSummary.graded_count.toLocaleString()}</p>
                  </div>
                  {Object.entries(metricsSummary.by_language).map(([lang, n]) => (
                    <div key={lang} className="metric-card">
                      <h3>Lang: {lang}</h3>
                      <p className="metric-number">{n.toLocaleString()}</p>
                    </div>
                  ))}
                </div>
                {tenRate && (
                  <div className="metrics-block">
                    <h3>Grade 10 rate</h3>
                    <p>
                      {tenRate.overall_ten_rate != null
                        ? `${(tenRate.overall_ten_rate * 100).toFixed(1)}% of graded sales are grade 10`
                        : "No graded sales"}
                      {tenRate.graded_count > 0 && (
                        <span className="muted"> ({tenRate.ten_count} / {tenRate.graded_count})</span>
                      )}
                    </p>
                    {Object.keys(tenRate.by_company).length > 0 && (
                      <ul className="ten-rate-list">
                        {Object.entries(tenRate.by_company).map(([company, rate]) => (
                          <li key={company}>
                            <strong>{company}</strong>: {(rate * 100).toFixed(1)}%
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
                {byGrade && byGrade.buckets.length > 0 && (
                  <div className="metrics-block">
                    <h3>By grade</h3>
                    <table className="metrics-table">
                      <thead>
                        <tr>
                          <th>Grade</th>
                          <th>Count</th>
                          <th>Median price (USD)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {byGrade.buckets.map((b) => (
                          <tr key={b.grade_label}>
                            <td>{b.grade_label}</td>
                            <td>{b.count.toLocaleString()}</td>
                            <td>{b.median_price_usd != null ? `$${b.median_price_usd.toFixed(2)}` : "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
                {byCompany && byCompany.buckets.length > 0 && (
                  <div className="metrics-block">
                    <h3>By grading company</h3>
                    <table className="metrics-table">
                      <thead>
                        <tr>
                          <th>Company</th>
                          <th>Count</th>
                          <th>Median (USD)</th>
                          <th>By grade</th>
                        </tr>
                      </thead>
                      <tbody>
                        {byCompany.buckets.map((b) => (
                          <tr key={b.company}>
                            <td><strong>{b.company}</strong></td>
                            <td>{b.count.toLocaleString()}</td>
                            <td>{b.median_price_usd != null ? `$${b.median_price_usd.toFixed(2)}` : "—"}</td>
                            <td>
                              {b.grade_breakdown.length > 0
                                ? b.grade_breakdown
                                    .map((g) => `${g.grade_value ?? "?"}: ${g.count} ($${g.median_price_usd?.toFixed(0) ?? "—"})`)
                                    .join(" · ")
                                : "—"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            )}
          </section>
        </main>
      ) : view === "movers" ? (
        <main className="main metrics-main">
          <section className="metrics-section">
            <h2>Big movers (raw price)</h2>
            <div className="metrics-filters">
              <label>
                Language{" "}
                <select
                  value={moversLang}
                  onChange={(e) => {
                    setMoversLang(e.target.value);
                    setMoversData(null);
                  }}
                >
                  <option value="">All</option>
                  <option value="en">English</option>
                  <option value="jp">Japanese</option>
                  <option value="other">Other</option>
                </select>
              </label>
              <input
                className="small-input"
                type="number"
                value={moversWindow}
                onChange={(e) => setMoversWindow(Number(e.target.value) || 30)}
                placeholder="window days"
              />
              <input
                className="small-input"
                type="number"
                value={moversMinNow}
                onChange={(e) => setMoversMinNow(Number(e.target.value) || 3)}
                placeholder="min sales now"
              />
              <input
                className="small-input"
                type="number"
                value={moversMinPrev}
                onChange={(e) => setMoversMinPrev(Number(e.target.value) || 3)}
                placeholder="min sales prev"
              />
              <button
                type="button"
                onClick={() => {
                  setMoversData(null);
                  loadMovers();
                }}
                disabled={moversLoading}
              >
                {moversLoading ? "Loading…" : "Refresh"}
              </button>
            </div>
            {moversError && <p className="error">{moversError}</p>}
            {moversData && moversData.cards.length > 0 && (
              <div className="card-block">
                <p className="muted">
                  Median raw price change over last {moversData.window_days} days vs previous{" "}
                  {moversData.window_days} days. Sorted by absolute % change.
                </p>
                <table className="metrics-table">
                  <thead>
                    <tr>
                      <th>Card</th>
                      <th>Now</th>
                      <th>Prev</th>
                      <th>Change %</th>
                      <th>Sales now</th>
                      <th>Sales prev</th>
                    </tr>
                  </thead>
                  <tbody>
                    {moversData.cards.map((m) => (
                      <tr key={m.card_id} className="clickable-row" onClick={() => loadCard(m.card_id, true)}>
                        <td>
                          <strong>{m.name}</strong>
                          {m.set_name && <div className="muted">{m.set_name}</div>}
                        </td>
                        <td>{m.value_now_usd != null ? `$${m.value_now_usd.toFixed(2)}` : "—"}</td>
                        <td>{m.value_prev_usd != null ? `$${m.value_prev_usd.toFixed(2)}` : "—"}</td>
                        <td className={m.change_pct != null && m.change_pct > 0 ? "pos" : "neg"}>
                          {m.change_pct != null ? `${(m.change_pct * 100).toFixed(1)}%` : "—"}
                        </td>
                        <td>{m.sales_now}</td>
                        <td>{m.sales_prev}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </main>
      ) : (
      <main className="main">
        <section className="search-section">
          <form onSubmit={handleSearch} className="search-form">
            <input
              type="text"
              placeholder="Search for a card (e.g., Charizard Base Set PSA 10)"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <button type="submit" disabled={loading}>
              {loading ? "Searching..." : "Search"}
            </button>
          </form>
          <div className="metrics-filters" style={{ marginTop: "0.5rem" }}>
            <label>
              Language{" "}
              <select value={cardsLang} onChange={(e) => setCardsLang(e.target.value)}>
                <option value="">All</option>
                <option value="en">English</option>
                <option value="jp">Japanese</option>
                <option value="other">Other</option>
              </select>
            </label>
          </div>
          {error && <p className="error">{error}</p>}

          {results.length > 0 && (
            <ul className="results-list">
              {results.map((r) => (
                <li key={r.card_id} onClick={() => loadCard(r.card_id)}>
                  <div className="result-row">
                    {r.image_url && (
                      <img
                        src={r.image_url}
                        alt={r.name}
                        className="result-thumb"
                        loading="lazy"
                      />
                    )}
                    <div>
                      <div className="result-title">
                        {r.name}
                        {r.variant && (
                          <span className="muted" style={{ marginLeft: "0.25rem", fontSize: "0.8rem" }}>
                            · {r.variant}
                          </span>
                        )}
                      </div>
                      <div className="result-meta">
                        {r.set_name}{r.number && r.number !== "-" ? ` · #${r.number}` : ""}
                        {typeof r.raw_median_usd === "number" && (r.raw_sales_count ?? 0) > 0 && (
                          <>
                            {" "}
                            · Raw: ${r.raw_median_usd.toFixed(2)}
                            {typeof r.raw_low_usd === "number" && typeof r.raw_high_usd === "number" && (
                              <> (L:{r.raw_low_usd.toFixed(2)} – H:{r.raw_high_usd.toFixed(2)})</>
                            )}
                            {" "}
                            ({r.raw_sales_count} sales)
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="detail-section">
          {selected ? (
            <div className="card-detail">
              <div className="card-detail-header">
                <div className="card-image-wrap">
                  {selected.image_url && !cardImageError ? (
                    <>
                      {!cardImageLoaded && (
                        <div className="card-image-placeholder card-image-loading">
                          <span>Loading image…</span>
                        </div>
                      )}
                      <img
                        src={selected.image_url}
                        alt={selected.name}
                        className="card-image"
                        style={{ opacity: cardImageLoaded ? 1 : 0 }}
                        onLoad={() => setCardImageLoaded(true)}
                        onError={() => setCardImageError(true)}
                      />
                    </>
                  ) : (
                    <div className="card-image-placeholder">
                      <span>Card image not available</span>
                    </div>
                  )}
                </div>
                <div className="card-detail-meta">
                  <h2>
                    {selected.name}
                    {selected.variant && (
                      <span className="muted" style={{ marginLeft: "0.5rem", fontSize: "0.85rem" }}>
                        · {selected.variant}
                      </span>
                    )}
                  </h2>
                  <div className="muted">
                    Set:{" "}
                    {selected.set_slug ? (
                      <button
                        type="button"
                        className="link-button"
                        onClick={() => {
                          if (typeof window !== "undefined") {
                            window.location.hash = `set=${encodeURIComponent(selected.set_slug as string)}`;
                          }
                          setView("sets");
                          loadCardsInSet(selected.set_slug as string);
                        }}
                      >
                        {selected.set_name}
                      </button>
                    ) : (
                      selected.set_name
                    )}
                    {selected.number && selected.number !== "-" && (
                      <> · #{selected.number}</>
                    )}
                  </div>
                  <p className="grade">
                    {selected.grade_company && selected.grade_value
                      ? `${selected.grade_company} ${selected.grade_value}`
                      : "Raw / unspecified grade"}
                  </p>
                </div>
              </div>

              {Array.isArray((selected as any).recent_sales) && (selected as any).recent_sales.length > 0 && (
                <div className="card-block">
                  <h3>Recent sales (contributing comps)</h3>
                  <table className="metrics-table">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Price (USD)</th>
                        <th>Grade</th>
                        <th>Cond</th>
                        <th>Title</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(selected as any).recent_sales.slice(0, 10).map((s: any, idx: number) => (
                        <tr key={idx}>
                          <td>{s.sold_at ? String(s.sold_at).slice(0, 10) : "—"}</td>
                          <td>{s.price_usd != null ? `$${Number(s.price_usd).toFixed(2)}` : "—"}</td>
                          <td>{s.grade_company ? `${s.grade_company} ${s.grade_value ?? ""}` : "Raw"}</td>
                          <td>{s.condition ?? "—"}</td>
                          <td className="muted">{s.title}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              <div className="metrics-grid">
                <div className="metric">
                  <h3>Fair Value Now</h3>
                  <p className="metric-value">
                    ${selected.fair_value_now.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </p>
                  <p className="metric-sub">
                    95% CI: ${selected.fair_value_ci_low.toLocaleString()} – $
                    {selected.fair_value_ci_high.toLocaleString()}
                  </p>
                </div>

                <div className="metric">
                  <h3>Liquidity Score</h3>
                  <p className="metric-value">{selected.liquidity_score}/100</p>
                  <p className="metric-sub">Higher = sells faster</p>
                </div>

                <div className="metric">
                  <h3>Risk Score</h3>
                  <p className="metric-value">{selected.risk_score}/100</p>
                  <p className="metric-sub">Higher = more volatile</p>
                </div>

                {(selected.change_30d_pct != null || selected.change_90d_pct != null) && (
                  <div className="metric">
                    <h3>Trend</h3>
                    <p className="metric-value">
                      {selected.change_30d_pct != null ? (
                        <span className={selected.change_30d_pct >= 0 ? "up" : "down"}>
                          {selected.change_30d_pct >= 0 ? "+" : ""}{(selected.change_30d_pct * 100).toFixed(1)}%
                        </span>
                      ) : "—"}
                      <span className="muted"> 30d</span>
                    </p>
                    <p className="metric-sub">
                      90d: {selected.change_90d_pct != null ? (
                        <span className={selected.change_90d_pct >= 0 ? "up" : "down"}>
                          {selected.change_90d_pct >= 0 ? "+" : ""}{(selected.change_90d_pct * 100).toFixed(1)}%
                        </span>
                      ) : "—"}
                    </p>
                  </div>
                )}

                {typeof selected.raw_median_usd === "number" && (selected.raw_sales_count ?? 0) > 0 && (
                  <div className="metric">
                    <h3>Raw value band</h3>
                    <p className="metric-value">
                      ${selected.raw_median_usd.toFixed(2)}
                    </p>
                    <p className="metric-sub">
                      Low ${selected.raw_low_usd != null ? selected.raw_low_usd.toFixed(2) : "—"} · High $
                      {selected.raw_high_usd != null ? selected.raw_high_usd.toFixed(2) : "—"} ·{" "}
                      {selected.raw_sales_count} sales
                    </p>
                  </div>
                )}
              </div>

              {selected.raw_by_condition && Object.keys(selected.raw_by_condition).length > 0 && (
                <div className="card-block">
                  <div className="set-cards-header">
                    <h3>Raw by condition</h3>
                    <label className="muted">
                      Sort:{" "}
                      <select
                        value={rawConditionSort}
                        onChange={(e) => setRawConditionSort(e.target.value as "condition" | "median" | "count")}
                      >
                        <option value="condition">Condition</option>
                        <option value="median">Median (high → low)</option>
                        <option value="count">Sales (most first)</option>
                      </select>
                    </label>
                  </div>
                  <p className="muted">Ungraded sales grouped by condition. Use &quot;Your raw condition&quot; in Grading upside to compare vs graded EV.</p>
                  <table className="metrics-table">
                    <thead>
                      <tr>
                        <th>Condition</th>
                        <th>Sales</th>
                        <th>Median (USD)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(() => {
                        const order = ["NM", "LP", "MP", "HP", "Damaged", "Unknown"];
                        let keys = order.filter((c) => selected.raw_by_condition && selected.raw_by_condition[c]);
                        if (rawConditionSort === "median") {
                          keys = [...keys].sort((a, b) => (selected.raw_by_condition![b].median_price_usd - selected.raw_by_condition![a].median_price_usd));
                        } else if (rawConditionSort === "count") {
                          keys = [...keys].sort((a, b) => selected.raw_by_condition![b].count - selected.raw_by_condition![a].count);
                        }
                        return keys.map((c) => (
                          <tr key={c}>
                            <td><strong>{c}</strong></td>
                            <td>{selected.raw_by_condition![c].count}</td>
                            <td>${selected.raw_by_condition![c].median_price_usd.toFixed(2)}</td>
                          </tr>
                        ));
                      })()}
                    </tbody>
                  </table>
                </div>
              )}

              {selected.recent_raw_by_condition && Object.keys(selected.recent_raw_by_condition).length > 0 && (
                <div className="card-block">
                  <div className="set-cards-header">
                    <h3>Recent raw values by condition</h3>
                    <p className="muted" style={{ margin: 0 }}>
                      Last {selected.recent_window_days ?? 90} days (median per condition).
                    </p>
                  </div>
                  <table className="metrics-table">
                    <thead>
                      <tr>
                        <th>Condition</th>
                        <th>Recent sales</th>
                        <th>Recent median (USD)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {["NM", "LP", "MP", "HP", "Damaged", "Unknown"]
                        .filter((c) => selected.recent_raw_by_condition && selected.recent_raw_by_condition[c])
                        .map((c) => (
                          <tr key={c}>
                            <td><strong>{c}</strong></td>
                            <td>{selected.recent_raw_by_condition![c].count}</td>
                            <td>${selected.recent_raw_by_condition![c].median_price_usd.toFixed(2)}</td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              )}

              {selected.history && selected.history.length > 1 && (
                <div className="card-block">
                  <div className="set-cards-header">
                    <h3>Market movement (toggle companies/grades)</h3>
                    <button type="button" onClick={() => loadFilteredSeries(selected)} disabled={seriesLoading}>
                      {seriesLoading ? "Loading…" : "Update chart"}
                    </button>
                  </div>

                  {!cardSeries && (
                    <div className="filters-row">
                      <span className="muted">Range:</span>
                      <button
                        type="button"
                        className={historyRange === "30d" ? "chip active" : "chip"}
                        onClick={() => setHistoryRange("30d")}
                      >
                        30d
                      </button>
                      <button
                        type="button"
                        className={historyRange === "90d" ? "chip active" : "chip"}
                        onClick={() => setHistoryRange("90d")}
                      >
                        90d
                      </button>
                      <button
                        type="button"
                        className={historyRange === "1y" ? "chip active" : "chip"}
                        onClick={() => setHistoryRange("1y")}
                      >
                        1y
                      </button>
                      <button
                        type="button"
                        className={historyRange === "all" ? "chip active" : "chip"}
                        onClick={() => setHistoryRange("all")}
                      >
                        All
                      </button>
                    </div>
                  )}

                  <div className="filters-row">
                    <label className="check">
                      <input
                        type="checkbox"
                        checked={seriesIncludeRaw}
                        onChange={(e) => setSeriesIncludeRaw(e.target.checked)}
                      />
                      Raw
                    </label>
                    {Object.keys(seriesCompanies).map((c) => (
                      <label key={c} className="check">
                        <input
                          type="checkbox"
                          checked={!!seriesCompanies[c]}
                          onChange={(e) => setSeriesCompanies((p) => ({ ...p, [c]: e.target.checked }))}
                        />
                        {c}
                      </label>
                    ))}
                  </div>

                  {seriesIncludeRaw && selected.raw_by_condition && Object.keys(selected.raw_by_condition).length > 0 && (
                    <div className="filters-row">
                      <span className="muted">Raw by condition:</span>
                      {["NM", "LP", "MP", "HP", "Damaged", "Unknown"]
                        .filter((c) => selected.raw_by_condition && selected.raw_by_condition[c])
                        .map((c) => (
                          <label key={c} className="check">
                            <input
                              type="checkbox"
                              checked={!!seriesRawConditions[c]}
                              onChange={(e) => setSeriesRawConditions((p) => ({ ...p, [c]: e.target.checked }))}
                            />
                            {c}
                          </label>
                        ))}
                    </div>
                  )}

                  <div className="filters-row">
                    <span className="muted">Grades:</span>
                    {Object.keys(seriesGrades).map((g) => (
                      <label key={g} className="check">
                        <input
                          type="checkbox"
                          checked={!!seriesGrades[g]}
                          onChange={(e) => setSeriesGrades((p) => ({ ...p, [g]: e.target.checked }))}
                        />
                        {g}
                      </label>
                    ))}
                  </div>

                  {seriesError && <p className="error">{seriesError}</p>}
                  {cardSeries ? (
                    <MultiLineChart
                      lines={cardSeries.series.map((s) => ({
                        label: s.label,
                        points: s.points.map((p) => ({ x: p.date, y: p.median_price_usd })),
                      }))}
                      height={200}
                    />
                  ) : (
                    <LineChart
                      points={(() => {
                        const all = selected.history!;
                        if (historyRange === "all") return all.map((p) => ({ x: p.date, y: p.median_price }));
                        const now = new Date(all[all.length - 1].date);
                        let cutoff = new Date(now);
                        if (historyRange === "30d") cutoff.setDate(cutoff.getDate() - 30);
                        else if (historyRange === "90d") cutoff.setDate(cutoff.getDate() - 90);
                        else cutoff.setFullYear(cutoff.getFullYear() - 1);
                        return all
                          .filter((p) => new Date(p.date) >= cutoff)
                          .map((p) => ({ x: p.date, y: p.median_price }));
                      })()}
                      height={180}
                      forecast={selected.forecast}
                    />
                  )}
                </div>
              )}

              {selected.prices_by_grade && selected.prices_by_grade.length > 0 && (
                <div className="card-block">
                  <h3>Grade grid (PriceCharting-style)</h3>
                  <GradeGrid pricesByGrade={selected.prices_by_grade} />
                </div>
              )}

              {selected.prices_by_grade && selected.prices_by_grade.length > 0 && (
                <div className="card-block">
                  <h3>Prices by grade (all companies)</h3>
                  <table className="metrics-table">
                    <thead>
                      <tr>
                        <th>Grade</th>
                        <th>Sales</th>
                        <th>Median (USD)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selected.prices_by_grade.map((p) => (
                        <tr key={p.label}>
                          <td><strong>{p.label}</strong></td>
                          <td>{p.count}</td>
                          <td>${p.median_price_usd.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {selected.recent_prices_by_grade && selected.recent_prices_by_grade.length > 0 && (
                <div className="card-block">
                  <h3>Recent prices by grade</h3>
                  <p className="muted">
                    Last {selected.recent_window_days ?? 90} days of graded sales (per company + grade).
                  </p>
                  <table className="metrics-table">
                    <thead>
                      <tr>
                        <th>Grade</th>
                        <th>Recent sales</th>
                        <th>Recent median (USD)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selected.recent_prices_by_grade.map((p) => (
                        <tr key={p.label}>
                          <td><strong>{p.label}</strong></td>
                          <td>{p.count}</td>
                          <td>${p.median_price_usd.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {selected.graded_price_bands && selected.graded_price_bands.length > 0 && (
                <div className="card-block">
                  <h3>Graded value band by company</h3>
                  <table className="metrics-table">
                    <thead>
                      <tr>
                        <th>Company</th>
                        <th>Low</th>
                        <th>Median</th>
                        <th>High</th>
                        <th>Sales</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selected.graded_price_bands.map((b) => (
                        <tr key={b.company}>
                          <td><strong>{b.company}</strong></td>
                          <td>{b.low_usd != null ? `$${b.low_usd.toFixed(2)}` : "—"}</td>
                          <td>{b.median_usd != null ? `$${b.median_usd.toFixed(2)}` : "—"}</td>
                          <td>{b.high_usd != null ? `$${b.high_usd.toFixed(2)}` : "—"}</td>
                          <td>{b.sales_count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {selected.grade_distribution && selected.grade_distribution.length > 0 && (
                <div className="card-block">
                  <h3>Grade distribution (sales count by company)</h3>
                  <ul className="grade-dist-list">
                    {selected.grade_distribution.map((d) => (
                      <li key={d.company}>
                        <strong>{d.company}</strong>: {d.total_graded} graded
                        {d.ten_rate != null && ` · 10 rate: ${(d.ten_rate * 100).toFixed(1)}%`}
                        {" — "}
                        {d.by_grade.map((g) => `${g.grade_value}: ${g.count}`).join(", ")}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {selected.grading_upside && (
                <div className="card-block grading-upside">
                  <h3>Grading upside (interactive)</h3>
                  <p className="muted">
                    Compare your raw cost to the expected graded value by company. EV already subtracts grading cost; upside is EV minus your raw cost.
                  </p>
                  <div className="grading-controls">
                    {selected.raw_by_condition && Object.keys(selected.raw_by_condition).length > 0 && (
                      <label>
                        Your raw condition
                        <select
                          value={selectedCondition ?? ""}
                          onChange={(e) => {
                            const value = e.target.value || null;
                            setSelectedCondition(value);
                            if (value && selected.raw_by_condition && selected.raw_by_condition[value]) {
                              setGradingPurchasePriceUsd(selected.raw_by_condition[value].median_price_usd);
                            }
                          }}
                        >
                          <option value="">Custom / unknown</option>
                          {["NM", "LP", "MP", "HP", "Damaged", "Unknown"]
                            .filter((c) => selected.raw_by_condition && selected.raw_by_condition[c])
                            .map((c) => (
                              <option key={c} value={c}>
                                {c} ({selected.raw_by_condition?.[c].count ?? 0} sales)
                              </option>
                            ))}
                        </select>
                      </label>
                    )}
                    <label>
                      Your raw cost (USD)
                      <input
                        type="number"
                        step="0.01"
                        value={gradingPurchasePriceUsd ?? ""}
                        onChange={(e) => setGradingPurchasePriceUsd(e.target.value ? Number(e.target.value) : null)}
                      />
                    </label>
                    <label>
                      Default grading cost (USD)
                      <input
                        type="number"
                        step="0.01"
                        value={gradingDefaultCostUsd}
                        onChange={(e) => setGradingDefaultCostUsd(Number(e.target.value) || 0)}
                      />
                    </label>
                  </div>

                  {selectedCondition && selected.raw_by_condition?.[selectedCondition] && (
                    <p className="muted">
                      Using <strong>{selectedCondition}</strong> median (${selected.raw_by_condition[selectedCondition].median_price_usd.toFixed(2)}, {selected.raw_by_condition[selectedCondition].count} sales) as your raw value. Override &quot;Your raw cost&quot; or set per-company grading cost to compare.
                    </p>
                  )}
                  <p className="muted">
                    EV uses this card’s observed grade distribution per company and median prices per company-grade bucket.
                  </p>

                  <table className="metrics-table">
                    <thead>
                      <tr>
                        <th>Company</th>
                        <th>EV (USD)</th>
                        <th>Upside (USD)</th>
                        <th>Worth grading?</th>
                        <th>Cost override</th>
                      </tr>
                    </thead>
                    <tbody>
                      {computeCompanyEV({
                        pricesByGrade: selected.prices_by_grade ?? [],
                        distributions: selected.grade_distribution ?? [],
                        rawCostUsd: gradingPurchasePriceUsd,
                        defaultGradingCostUsd: gradingDefaultCostUsd,
                        gradingCostByCompany,
                      }).map((row) => (
                        <tr key={row.company}>
                          <td><strong>{row.company}</strong></td>
                          <td>${row.evUsd.toFixed(2)}</td>
                          <td>{row.upsideUsd >= 0 ? `+${row.upsideUsd.toFixed(2)}` : row.upsideUsd.toFixed(2)}</td>
                          <td>{row.worthGrading ? "Yes" : "No"}</td>
                          <td>
                            <input
                              className="small-input"
                              type="number"
                              step="0.01"
                              value={gradingCostByCompany[row.company] ?? ""}
                              placeholder={`${gradingDefaultCostUsd}`}
                              onChange={(e) => {
                                const v = e.target.value ? Number(e.target.value) : NaN;
                                setGradingCostByCompany((prev) => {
                                  const next = { ...prev };
                                  if (!Number.isFinite(v)) delete next[row.company];
                                  else next[row.company] = v;
                                  return next;
                                });
                              }}
                            />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              <div className="placeholder-chart">
                <p>Price chart and forecast bands will appear here.</p>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <p>Search for a card and select a result to see details.</p>
            </div>
          )}
        </section>
      </main>
      )}
    </div>
  );
};

function LineChart({
  points,
  height,
  forecast,
}: {
  points: { x: string; y: number }[];
  height: number;
  forecast?: { date: string; p10: number; p50: number; p90: number }[];
}) {
  const width = 640;
  const padding = 24;
  const mainLinePoints = forecast?.length
    ? [...points, ...forecast.map((f) => ({ x: f.date, y: f.p50 }))]
    : points;
  const ys = mainLinePoints.map((p) => p.y);
  const bandYs = forecast?.flatMap((f) => [f.p10, f.p90]) ?? [];
  const minY = Math.min(...ys, ...bandYs);
  const maxY = Math.max(...ys, ...bandYs);
  const spanY = maxY - minY || 1;
  const spanX = Math.max(1, mainLinePoints.length - 1);

  const coords = mainLinePoints.map((p, i) => {
    const x = padding + (i / spanX) * (width - padding * 2);
    const y = padding + (1 - (p.y - minY) / spanY) * (height - padding * 2);
    return { x, y, label: p.x, value: p.y };
  });

  const path = coords
    .map((c, i) => `${i === 0 ? "M" : "L"} ${c.x.toFixed(2)} ${c.y.toFixed(2)}`)
    .join(" ");

  let bandPath: string | null = null;
  if (forecast?.length && points.length > 0) {
    const startIdx = points.length;
    const endIdx = mainLinePoints.length - 1;
    const x = (i: number) => padding + (i / spanX) * (width - padding * 2);
    const y = (v: number) => padding + (1 - (v - minY) / spanY) * (height - padding * 2);
    const first = forecast[0];
    const last = forecast[forecast.length - 1];
    bandPath = [
      `M ${x(startIdx).toFixed(2)} ${y(first.p10).toFixed(2)}`,
      `L ${x(endIdx).toFixed(2)} ${y(last.p10).toFixed(2)}`,
      `L ${x(endIdx).toFixed(2)} ${y(last.p90).toFixed(2)}`,
      `L ${x(startIdx).toFixed(2)} ${y(first.p90).toFixed(2)}`,
      "Z",
    ].join(" ");
  }

  return (
    <div className="chart-wrap">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Price history chart">
        {bandPath && (
          <path d={bandPath} fill="rgba(56, 189, 248, 0.2)" stroke="none" />
        )}
        <path d={path} fill="none" stroke="rgba(56, 189, 248, 0.95)" strokeWidth="2.5" />
        {coords.map((c, i) => (
          <circle key={i} cx={c.x} cy={c.y} r="2.5" fill="rgba(56, 189, 248, 0.95)" />
        ))}
      </svg>
      <div className="chart-legend muted">
        <span>Min: ${minY.toFixed(2)}</span>
        <span>Max: ${maxY.toFixed(2)}</span>
        <span>Points: {mainLinePoints.length}</span>
        {forecast?.length ? <span>Forecast band (p10–p90)</span> : null}
      </div>
    </div>
  );
}

function MultiLineChart({
  lines,
  height,
}: {
  lines: { label: string; points: { x: string; y: number }[] }[];
  height: number;
}) {
  const width = 640;
  const padding = 24;
  const all = lines.flatMap((l) => l.points.map((p) => p.y));
  const minY = Math.min(...all);
  const maxY = Math.max(...all);
  const spanY = maxY - minY || 1;

  const maxLen = Math.max(...lines.map((l) => l.points.length));
  const spanX = Math.max(1, maxLen - 1);

  const palette = [
    "rgba(56, 189, 248, 0.95)",
    "rgba(34, 197, 94, 0.95)",
    "rgba(168, 85, 247, 0.95)",
    "rgba(251, 191, 36, 0.95)",
    "rgba(244, 63, 94, 0.95)",
    "rgba(148, 163, 184, 0.95)",
  ];

  function pathFor(points: { x: string; y: number }[]) {
    return points
      .map((p, i) => {
        const x = padding + (i / spanX) * (width - padding * 2);
        const y = padding + (1 - (p.y - minY) / spanY) * (height - padding * 2);
        return `${i === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
      })
      .join(" ");
  }

  return (
    <div className="chart-wrap">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Market movement chart">
        {lines.map((l, idx) => (
          <path
            key={l.label}
            d={pathFor(l.points)}
            fill="none"
            stroke={palette[idx % palette.length]}
            strokeWidth="2.5"
          />
        ))}
      </svg>
      <div className="chart-legend muted">
        <span>Min: ${minY.toFixed(2)}</span>
        <span>Max: ${maxY.toFixed(2)}</span>
        <span>Lines: {lines.length}</span>
      </div>
      <div className="legend-row">
        {lines.map((l, idx) => (
          <div key={l.label} className="legend-item">
            <span className="swatch" style={{ background: palette[idx % palette.length] }} />
            {l.label}
          </div>
        ))}
      </div>
    </div>
  );
}

function formatGradeLabel(v: number) {
  return v === Math.trunc(v) ? String(Math.trunc(v)) : String(v);
}

function GradeGrid({ pricesByGrade }: { pricesByGrade: PriceByGrade[] }) {
  // companies from data (excluding raw)
  const companies = Array.from(
    new Set(pricesByGrade.filter((p) => p.grade_company).map((p) => p.grade_company as string))
  ).sort();

  const gradeValues = Array.from(
    new Set(
      pricesByGrade
        .filter((p) => p.grade_company && p.grade_value != null)
        .map((p) => p.grade_value as number)
    )
  );

  // Ensure common grade columns exist (even if empty)
  for (const g of [10, 9.5, 9]) {
    if (!gradeValues.includes(g)) gradeValues.push(g);
  }
  gradeValues.sort((a, b) => b - a);

  const raw = pricesByGrade.find((p) => p.label === "Ungraded") ?? null;

  const cellMap = new Map<string, PriceByGrade>();
  for (const p of pricesByGrade) {
    if (!p.grade_company || p.grade_value == null) continue;
    cellMap.set(`${p.grade_company}:${p.grade_value}`, p);
  }

  return (
    <div className="grid-scroll">
      <table className="grid-table">
        <thead>
          <tr>
            <th className="sticky-col">Company</th>
            <th>Ungraded</th>
            {gradeValues.map((g) => (
              <th key={g}>{formatGradeLabel(g)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          <tr>
            <td className="sticky-col"><strong>Raw</strong></td>
            <td>
              {raw ? (
                <div className="grid-cell">
                  <div className="grid-price">${raw.median_price_usd.toFixed(0)}</div>
                  <div className="grid-meta">{raw.count} sale(s)</div>
                </div>
              ) : (
                "—"
              )}
            </td>
            {gradeValues.map((g) => (
              <td key={`raw-${g}`} className="grid-empty">—</td>
            ))}
          </tr>
          {companies.map((company) => (
            <tr key={company}>
              <td className="sticky-col"><strong>{company}</strong></td>
              <td className="grid-empty">—</td>
              {gradeValues.map((g) => {
                const cell = cellMap.get(`${company}:${g}`) ?? null;
                return (
                  <td key={`${company}-${g}`}>
                    {cell ? (
                      <div className="grid-cell">
                        <div className="grid-price">${cell.median_price_usd.toFixed(0)}</div>
                        <div className="grid-meta">{cell.count} sale(s)</div>
                      </div>
                    ) : (
                      <span className="grid-empty">—</span>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function computeCompanyEV({
  pricesByGrade,
  distributions,
  rawCostUsd,
  defaultGradingCostUsd,
  gradingCostByCompany,
}: {
  pricesByGrade: PriceByGrade[];
  distributions: CompanyGradeDistribution[];
  rawCostUsd: number | null;
  defaultGradingCostUsd: number;
  gradingCostByCompany: Record<string, number>;
}): { company: string; evUsd: number; upsideUsd: number; worthGrading: boolean }[] {
  const priceMap = new Map<string, number>();
  for (const p of pricesByGrade) {
    if (!p.grade_company || p.grade_value == null) continue;
    priceMap.set(`${p.grade_company}:${p.grade_value}`, p.median_price_usd);
  }
  const rawMedian = pricesByGrade.find((p) => p.label === "Ungraded")?.median_price_usd ?? 0;
  const raw = rawCostUsd ?? rawMedian;

  const out = [];
  for (const d of distributions) {
    const total = d.total_graded || d.by_grade.reduce((a, b) => a + b.count, 0);
    if (!total) continue;
    let ev = 0;
    for (const g of d.by_grade) {
      const price = priceMap.get(`${d.company}:${g.grade_value}`) ?? 0;
      ev += (g.count / total) * price;
    }
    const cost = gradingCostByCompany[d.company] ?? defaultGradingCostUsd;
    const upside = ev - raw - cost;
    out.push({ company: d.company, evUsd: ev, upsideUsd: upside, worthGrading: upside > 0 });
  }
  out.sort((a, b) => b.upsideUsd - a.upsideUsd);
  return out;
}

