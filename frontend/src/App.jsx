import { useEffect, useMemo, useState } from "react";
import "./App.css";

const API_URL = (
  import.meta.env.VITE_API_URL || "http://localhost:8000"
).replace(/\/$/, "");

const API_KEY = import.meta.env.VITE_API_KEY || "";

const MODEL_VERSION = "v1.2";
const MAX_BATCH_SIZE = 100;

const ICONS = {
  dashboard:
    "M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z",
  single:
    "M4 5h16v11H9l-5 4z",
  batch:
    "M12 3l9 5-9 5-9-5zM3 13l9 5 9-5",
  analytics:
    "M4 20V10M10 20V4M16 20v-7M22 20H2",
  status:
    "M3 12h4l3-8 4 16 3-8h4",
  send:
    "M22 2L11 13M22 2l-7 20-4-9-9-4z",
  route:
    "M6 17a2 2 0 1 0 0 4 2 2 0 0 0 0-4M18 3a2 2 0 1 0 0 4 2 2 0 0 0 0-4M8 19h7a3 3 0 0 0 0-6H9a3 3 0 0 1 0-6h7",
  alert:
    "M12 3l10 18H2zM12 10v5M12 18h.01",

  payment_refund:
    "M2 5h20v14H2zM2 10h20M6 15h4",
  order_missing_wrong:
    "M21 8l-9-5-9 5v8l9 5 9-5zM3 8l9 5 9-5M12 13v8",
  delivery_delay:
    "M3 6h11v10H3zM14 10h4l3 3v3h-7M7 16a2 2 0 1 0 0 4 2 2 0 0 0 0-4M17 16a2 2 0 1 0 0 4 2 2 0 0 0 0-4",
  food_quality:
    "M4 11h16a8 8 0 0 1-16 0zM9 4c0 1.5 1 1.5 1 3M14 4c0 1.5 1 1.5 1 3",
  app_technical:
    "M7 2h10v20H7zM11 18h2",
  account_promo:
    "M12 4a4 4 0 1 0 0 8 4 4 0 0 0 0-8M4 21a8 8 0 0 1 16 0",
  lost_item:
    "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14M21 21l-5-5",
  ride_trip_issue:
    "M5 17h14v-5l-2-5H7l-2 5zM5 12h14M8 15.5h.01M16 15.5h.01",
  safety_conduct:
    "M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z",
  general_inquiry:
    "M4 5h16v11H9l-5 4z",
  spam_irrelevant:
    "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18M5.6 5.6l12.8 12.8",
};

const NAV = [
  ["dashboard", "Dashboard", "Support routing dashboard"],
  ["single", "Single ticket", "Single ticket analysis"],
  ["batch", "Batch analysis", "Batch ticket analysis"],
  ["analytics", "Analytics", "Ticket analytics"],
  ["status", "System status", "System status"],
];

const formatLabel = (value) => {
  if (!value) return "None";

  return String(value)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
};

const pct = (value) =>
  Math.round((value || 0) * 100);

const getHeaders = () => {
  const headers = {
    "Content-Type": "application/json",
  };

  if (API_KEY) {
    headers["X-API-Key"] = API_KEY;
  }

  return headers;
};

const getErrorMessage = async (
  response,
  fallback = "Request failed."
) => {
  try {
    const data = await response.json();

    if (typeof data?.detail === "string") {
      return data.detail;
    }

    return (
      data?.error?.message ||
      data?.detail?.message ||
      fallback
    );
  } catch {
    return fallback;
  }
};

function Icon({ name, size = 18 }) {
  return (
    <svg
      className="ico"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        d={
          ICONS[name] ||
          ICONS.general_inquiry
        }
      />
    </svg>
  );
}

function Panel({
  label,
  title,
  chip,
  children,
  className = "",
  i = 0,
}) {
  return (
    <div
      className={`panel ${className}`}
      style={{ "--i": i }}
    >
      {(label || title || chip) && (
        <div className="panel-header">
          <div>
            {label && (
              <p className="panel-label">
                {label}
              </p>
            )}

            {title && (
              <h2>{title}</h2>
            )}
          </div>

          {chip}
        </div>
      )}

      {children}
    </div>
  );
}

function Stat({
  label,
  value,
  note,
  i = 0,
}) {
  return (
    <div
      className="stat-card"
      style={{ "--i": i }}
    >
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{note}</small>
    </div>
  );
}

function Empty({ title, text }) {
  return (
    <div className="empty-result">
      <div className="result-icon">
        <Icon
          name="route"
          size={25}
        />
      </div>

      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}

function ConfidenceRing({ value = 0 }) {
  const percent = pct(value);

  return (
    <div className="confidence-ring">
      <svg viewBox="0 0 120 120">
        <circle
          cx="60"
          cy="60"
          r="50"
          className="ring-track"
        />

        <circle
          cx="60"
          cy="60"
          r="50"
          className="ring-value"
          style={{
            "--offset":
              314 -
              314 *
                Math.min(
                  1,
                  Math.max(0, value)
                ),
          }}
        />
      </svg>

      <div className="ring-number">
        <strong>{percent}%</strong>
        <span>confidence</span>
      </div>
    </div>
  );
}

function App() {
  const [
    activeView,
    setActiveView,
  ] = useState("dashboard");

  const [
    health,
    setHealth,
  ] = useState(null);

  const [
    healthLoading,
    setHealthLoading,
  ] = useState(false);

  const [
    healthError,
    setHealthError,
  ] = useState("");

  const [
    channel,
    setChannel,
  ] = useState("email");

  const [
    subject,
    setSubject,
  ] = useState("");

  const [
    text,
    setText,
  ] = useState("");

  const [
    result,
    setResult,
  ] = useState(null);

  const [
    loading,
    setLoading,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState("");

  const [
    batchText,
    setBatchText,
  ] = useState("");

  const [
    batchResults,
    setBatchResults,
  ] = useState([]);

  const [
    batchLoading,
    setBatchLoading,
  ] = useState(false);

  const [
    batchError,
    setBatchError,
  ] = useState("");

  const online =
    health?.status === "ok";

  const checkHealth = async () => {
    setHealthLoading(true);
    setHealthError("");

    try {
      const response =
        await fetch(
          `${API_URL}/health`
        );

      if (!response.ok) {
        throw new Error(
          "Health check failed."
        );
      }

      const data =
        await response.json();

      setHealth(data);
    } catch (err) {
      setHealth(null);

      setHealthError(
        err.message ||
          "Unable to reach API."
      );
    } finally {
      setHealthLoading(false);
    }
  };

  useEffect(() => {
    checkHealth();
  }, []);

  const analyzeTicket = async () => {
    if (!text.trim()) {
      setError(
        "Ticket message is required."
      );

      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response =
        await fetch(
          `${API_URL}/predict`,
          {
            method: "POST",

            headers:
              getHeaders(),

            body:
              JSON.stringify({
                ticket_id: `WEB-${Date.now()}`,
                channel,
                subject:
                  subject.trim(),
                text:
                  text.trim(),
              }),
          }
        );

      if (!response.ok) {
        throw new Error(
          await getErrorMessage(
            response,
            "Prediction failed."
          )
        );
      }

      const data =
        await response.json();

      setResult(data);
    } catch (err) {
      setError(
        err.message ||
          "Unable to connect to API."
      );
    } finally {
      setLoading(false);
    }
  };

  const clearSingle = () => {
    setSubject("");
    setText("");
    setResult(null);
    setError("");
  };

  const batchLines = useMemo(
    () =>
      batchText
        .split("\n")
        .map((line) =>
          line.trim()
        )
        .filter(Boolean),
    [batchText]
  );

  const batchCount =
    batchLines.length;

  const analyzeBatch = async () => {
    if (batchCount === 0) {
      setBatchError(
        "Enter at least one ticket."
      );

      return;
    }

    if (
      batchCount >
      MAX_BATCH_SIZE
    ) {
      setBatchError(
        `Maximum ${MAX_BATCH_SIZE} tickets are allowed for synchronous batch analysis.`
      );

      return;
    }

    setBatchLoading(true);
    setBatchError("");
    setBatchResults([]);

    try {
      const timestamp =
        Date.now();

      const tickets =
        batchLines.map(
          (line, index) => ({
            ticket_id: `BATCH-${timestamp}-${index + 1}`,
            channel: "email",
            subject: "",
            text: line,
          })
        );

      const response =
        await fetch(
          `${API_URL}/predict/batch`,
          {
            method: "POST",

            headers:
              getHeaders(),

            body:
              JSON.stringify({
                tickets,
              }),
          }
        );

      if (!response.ok) {
        throw new Error(
          await getErrorMessage(
            response,
            "Batch prediction failed."
          )
        );
      }

      const data =
        await response.json();

      setBatchResults(
        Array.isArray(data)
          ? data
          : data.predictions ||
              data.results ||
              []
      );
    } catch (err) {
      setBatchError(
        err.message ||
          "Unable to run batch prediction."
      );
    } finally {
      setBatchLoading(false);
    }
  };

  const clearBatch = () => {
    setBatchText("");
    setBatchResults([]);
    setBatchError("");
  };

  const analytics = useMemo(
    () => {
      const total =
        batchResults.length;

      const urgentCount =
        batchResults.filter(
          (item) =>
            item.is_urgent
        ).length;

      const normalCount =
        total -
        urgentCount;

      const avgConfidence =
        total > 0
          ? pct(
              batchResults.reduce(
                (
                  sum,
                  item
                ) =>
                  sum +
                  (item.confidence ||
                    0),
                0
              ) / total
            )
          : 0;

      const counts = {};

      batchResults.forEach(
        (item) => {
          const category =
            item.category ||
            "unknown";

          counts[category] =
            (counts[
              category
            ] || 0) + 1;
        }
      );

      return {
        total,
        urgentCount,
        normalCount,
        avgConfidence,

        categoryEntries:
          Object.entries(
            counts
          ).sort(
            (a, b) =>
              b[1] - a[1]
          ),
      };
    },
    [batchResults]
  );

  const renderDashboard = () => (
    <section className="dashboard-page">
      <div className="hero-section">
        <div className="hero-content">
          <span className="hero-pill">
            AI Support Intelligence
          </span>

          <h1 className="hero-title">
            AI Support Ticket
            <span>
              {" "}
              Classifier & Router
            </span>
          </h1>

          <p className="hero-description">
            RouteIQ classifies
            multilingual customer
            support tickets, detects
            urgent requests, and routes
            each ticket to the correct
            support team.
          </p>

          <div className="hero-actions">
            <button
              className="primary-btn"
              onClick={() =>
                setActiveView(
                  "single"
                )
              }
            >
              <Icon
                name="single"
                size={17}
              />

              Analyze one ticket
            </button>

            <button
              className="secondary-btn"
              onClick={() =>
                setActiveView(
                  "batch"
                )
              }
            >
              <Icon
                name="batch"
                size={17}
              />

              Analyze batch
            </button>
          </div>
        </div>

        <div className="hero-visual">
          <div className="floating-card fc-1">
            <Icon
              name="single"
              size={21}
            />

            <div>
              <span>Customer ticket</span>
              <strong>
                “My order is late”
              </strong>
            </div>
          </div>

          <div className="flow-arrow">
            ↓
          </div>

          <div className="floating-card fc-2">
            <Icon
              name="delivery_delay"
              size={21}
            />

            <div>
              <span>
                AI classification
              </span>

              <strong>
                Delivery Delay
              </strong>
            </div>
          </div>

          <div className="flow-arrow">
            ↓
          </div>

          <div className="floating-card fc-3">
            <Icon
              name="route"
              size={21}
            />

            <div>
              <span>
                Routed team
              </span>

              <strong>
                Delivery Operations
              </strong>
            </div>
          </div>
        </div>
      </div>

      <div className="stats-grid">
        <Stat
          i={0}
          label="Category accuracy"
          value="88.1%"
          note="Validation-tuned score"
        />

        <Stat
          i={1}
          label="Urgency accuracy"
          value="97.1%"
          note="Validation accuracy"
        />

        <Stat
          i={2}
          label="Ticket categories"
          value="11"
          note="Automated routing classes"
        />

        <Stat
          i={3}
          label="API status"
          value={
            online
              ? "Healthy"
              : "Offline"
          }
          note="Live backend health"
        />
      </div>

      <div className="two-col">
        <Panel
          i={4}
          label="How it works"
          title="From ticket to team in seconds"
        >
          <div className="step-flow">
            <div className="step-item">
              <div className="step-number">
                1
              </div>

              <div>
                <strong>
                  Ticket Input
                </strong>

                <p>
                  Customer message
                  enters RouteIQ.
                </p>
              </div>
            </div>

            <div className="step-line" />

            <div className="step-item">
              <div className="step-number">
                2
              </div>

              <div>
                <strong>
                  AI Classification
                </strong>

                <p>
                  Detect category
                  and urgency.
                </p>
              </div>
            </div>

            <div className="step-line" />

            <div className="step-item">
              <div className="step-number">
                3
              </div>

              <div>
                <strong>
                  Team Routing
                </strong>

                <p>
                  Send to the
                  correct support
                  team.
                </p>
              </div>
            </div>
          </div>
        </Panel>

        <Panel
          i={5}
          label="Languages"
          title="Multilingual support"
        >
          <div className="language-cloud">
            {[
              "English",
              "Sinhala",
              "Tamil",
              "Singlish",
              "Tanglish",
              "Mixed",
            ].map((language) => (
              <span key={language}>
                {language}
              </span>
            ))}
          </div>

          <p className="language-note">
            Built for multilingual
            customer support text
            common in Sri Lanka.
          </p>
        </Panel>
      </div>
    </section>
  );

  const renderSingle = () => (
    <section>
      <div className="stats-grid compact-stats">
        <Stat
          i={0}
          label="API"
          value={
            online
              ? "Healthy"
              : "Offline"
          }
          note="Live connection"
        />

        <Stat
          i={1}
          label="Model"
          value={
            health?.model_version ||
            MODEL_VERSION
          }
          note="Active inference"
        />

        <Stat
          i={2}
          label="Categories"
          value="11"
          note="Primary classes"
        />

        <Stat
          i={3}
          label="Mode"
          value="Real-time"
          note="Single prediction"
        />
      </div>

      <div className="workspace-grid">
        <Panel
          i={0}
          label="Single Ticket"
          title="Analyze a support request"
          chip={
            <span className="panel-chip live">
              Live inference
            </span>
          }
        >
          <div className="form-grid">
            <div className="form-group">
              <label>
                Channel
              </label>

              <select
                value={channel}
                onChange={(e) =>
                  setChannel(
                    e.target.value
                  )
                }
              >
                <option value="email">
                  Email
                </option>

                <option value="chat">
                  Chat
                </option>

                <option value="call_transcript">
                  Call Transcript
                </option>
              </select>
            </div>

            <div className="form-group">
              <label>
                Subject
              </label>

              <input
                value={subject}
                onChange={(e) =>
                  setSubject(
                    e.target.value
                  )
                }
                placeholder="Example: Duplicate payment"
              />
            </div>

            <div className="form-group full-width">
              <label>
                Customer message
              </label>

              <div
                className={`field-wrap ${
                  loading
                    ? "scanning"
                    : ""
                }`}
              >
                <textarea
                  rows="8"
                  value={text}
                  onChange={(e) =>
                    setText(
                      e.target.value
                    )
                  }
                  placeholder="Paste the support ticket here..."
                />
              </div>
            </div>
          </div>

          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          <div className="action-row">
            <div className="request-preview">
              <span>
                {text.trim()
                  ? "Ready to analyze"
                  : "Waiting for ticket"}
              </span>

              <small>
                {text.length} characters
              </small>
            </div>

            <div className="btn-row">
              <button
                className="ghost-btn"
                onClick={
                  clearSingle
                }
              >
                Clear
              </button>

              <button
                className="primary-btn"
                onClick={
                  analyzeTicket
                }
                disabled={
                  loading ||
                  !text.trim()
                }
              >
                {loading ? (
                  <span className="spinner" />
                ) : (
                  <Icon
                    name="send"
                    size={16}
                  />
                )}

                {loading
                  ? "Analyzing..."
                  : "Analyze ticket"}
              </button>
            </div>
          </div>
        </Panel>

        <Panel
          i={1}
          className="result-panel"
          label="Prediction"
          title="Routing decision"
          chip={
            result?.model_version && (
              <span className="panel-chip">
                Model{" "}
                {
                  result.model_version
                }
              </span>
            )
          }
        >
          {!result ? (
            <Empty
              title={
                loading
                  ? "Running AI analysis..."
                  : "Ready for analysis"
              }
              text="RouteIQ will show the predicted category, urgency, confidence and support team here."
            />
          ) : (
            <div className="prediction-result">
              <div className="prediction-top">
                <ConfidenceRing
                  value={
                    result.confidence
                  }
                />

                <div className="prediction-main">
                  <span>
                    Primary category
                  </span>

                  <h3>
                    <Icon
                      name={
                        result.category
                      }
                      size={20}
                    />

                    {formatLabel(
                      result.category
                    )}
                  </h3>

                  {result.is_urgent && (
                    <span className="urgent-badge">
                      <Icon
                        name="alert"
                        size={14}
                      />
                      Urgent
                    </span>
                  )}
                </div>
              </div>

              <div className="route-visual">
                <div className="route-node">
                  Ticket
                </div>

                <div className="route-line">
                  <i />
                </div>

                <div className="route-node category-node">
                  {formatLabel(
                    result.category
                  )}
                </div>

                <div className="route-line">
                  <i />
                </div>

                <div className="route-node team-node">
                  {result.team}
                </div>
              </div>

              <div className="prediction-grid">
                <div className="prediction-card">
                  <span>
                    Assigned Team
                  </span>

                  <strong>
                    {result.team ||
                      "—"}
                  </strong>
                </div>

                <div className="prediction-card">
                  <span>
                    Urgency
                  </span>

                  <strong
                    className={
                      result.is_urgent
                        ? "urgent-text"
                        : "normal-text"
                    }
                  >
                    {result.is_urgent
                      ? "Urgent"
                      : "Normal"}
                  </strong>
                </div>

                <div className="prediction-card">
                  <span>
                    Secondary
                  </span>

                  <strong>
                    {formatLabel(
                      result.secondary_category
                    )}
                  </strong>
                </div>

                <div className="prediction-card">
                  <span>
                    Model
                  </span>

                  <strong>
                    {result.model_version ||
                      MODEL_VERSION}
                  </strong>
                </div>
              </div>

              <p className="confidence-note">
                Confidence is a
                decision-score based
                indicator, not a
                calibrated probability.
              </p>
            </div>
          )}
        </Panel>
      </div>
    </section>
  );

  const renderBatch = () => (
    <section>
      <Panel
        i={0}
        label="Batch Analysis"
        title="Analyze multiple support tickets"
        chip={
          <span className="panel-chip">
            /predict/batch
          </span>
        }
      >
        <div className="form-group">
          <label>
            One ticket per line
          </label>

          <div
            className={`field-wrap ${
              batchLoading
                ? "scanning"
                : ""
            }`}
          >
            <textarea
              rows="7"
              value={batchText}
              onChange={(e) =>
                setBatchText(
                  e.target.value
                )
              }
              placeholder={`I was charged twice and need a refund.
My food order has not arrived yet.
Connection is fine but the food menu is not loading.
The driver behaved inappropriately.`}
            />
          </div>
        </div>

        {batchError && (
          <div className="error-message">
            {batchError}
          </div>
        )}

        <div className="action-row">
          <div className="request-preview">
            <span>
              {batchCount} ticket
              {batchCount === 1
                ? ""
                : "s"}{" "}
              ready
            </span>

            <small>
              Up to{" "}
              {MAX_BATCH_SIZE}{" "}
              tickets per synchronous
              request
            </small>
          </div>

          <div className="btn-row">
            <button
              className="ghost-btn"
              onClick={
                clearBatch
              }
            >
              Clear
            </button>

            <button
              className="primary-btn"
              onClick={
                analyzeBatch
              }
              disabled={
                batchLoading ||
                batchCount === 0
              }
            >
              {batchLoading ? (
                <span className="spinner" />
              ) : (
                <Icon
                  name="send"
                  size={16}
                />
              )}

              {batchLoading
                ? "Analyzing..."
                : "Run batch analysis"}
            </button>
          </div>
        </div>
      </Panel>

      <Panel
        i={1}
        className="batch-result-panel"
        label="Results"
        title="Routing predictions"
        chip={
          batchResults.length >
            0 && (
            <span className="panel-chip live">
              {
                batchResults.length
              }{" "}
              predictions
            </span>
          )
        }
      >
        {batchResults.length ===
        0 ? (
          <Empty
            title="No batch results yet"
            text="Run batch analysis to view categories, urgency and support-team routing."
          />
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Category</th>
                  <th>Team</th>
                  <th>Urgency</th>
                  <th>
                    Confidence
                  </th>
                  <th>Model</th>
                </tr>
              </thead>

              <tbody>
                {batchResults.map(
                  (
                    item,
                    index
                  ) => (
                    <tr
                      key={
                        item.ticket_id ||
                        index
                      }
                    >
                      <td className="dim">
                        {index + 1}
                      </td>

                      <td>
                        <span className="cell-icon">
                          <Icon
                            name={
                              item.category
                            }
                            size={
                              16
                            }
                          />

                          {formatLabel(
                            item.category
                          )}
                        </span>
                      </td>

                      <td>
                        {item.team}
                      </td>

                      <td
                        className={
                          item.is_urgent
                            ? "urgent-text"
                            : "normal-text"
                        }
                      >
                        {item.is_urgent
                          ? "Urgent"
                          : "Normal"}
                      </td>

                      <td>
                        {pct(
                          item.confidence
                        )}
                        %
                      </td>

                      <td className="dim">
                        {item.model_version ||
                          MODEL_VERSION}
                      </td>
                    </tr>
                  )
                )}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </section>
  );

  const renderAnalytics = () => {
    const {
      total,
      urgentCount,
      normalCount,
      avgConfidence,
      categoryEntries,
    } = analytics;

    return (
      <section>
        <div className="stats-grid">
          <Stat
            label="Analyzed Tickets"
            value={total}
            note="Current session"
          />

          <Stat
            label="Urgent Tickets"
            value={urgentCount}
            note="Priority routing"
          />

          <Stat
            label="Normal Tickets"
            value={normalCount}
            note="Standard routing"
          />

          <Stat
            label="Avg Confidence"
            value={`${avgConfidence}%`}
            note="Decision-score indicator"
          />
        </div>

        <div className="two-col">
          <Panel
            label="Categories"
            title="Ticket distribution"
          >
            {categoryEntries.length ===
            0 ? (
              <Empty
                title="No analytics yet"
                text="Run batch analysis first."
              />
            ) : (
              <div className="bars">
                {categoryEntries.map(
                  ([
                    category,
                    count,
                  ]) => {
                    const percentage =
                      pct(
                        count /
                          total
                      );

                    return (
                      <div
                        className="bar-item"
                        key={
                          category
                        }
                      >
                        <div className="bar-head">
                          <span>
                            {formatLabel(
                              category
                            )}
                          </span>

                          <strong>
                            {count} ·{" "}
                            {
                              percentage
                            }
                            %
                          </strong>
                        </div>

                        <div className="bar-track">
                          <div
                            className="bar-fill"
                            style={{
                              "--bar":
                                `${percentage}%`,
                            }}
                          />
                        </div>
                      </div>
                    );
                  }
                )}
              </div>
            )}
          </Panel>

          <Panel
            label="Priority"
            title="Urgency overview"
          >
            {total === 0 ? (
              <Empty
                title="Waiting for results"
                text="Batch results will appear here."
              />
            ) : (
              <div className="priority-grid">
                <div className="priority-card urgent-card">
                  <span>
                    Urgent
                  </span>

                  <strong>
                    {urgentCount}
                  </strong>
                </div>

                <div className="priority-card normal-card">
                  <span>
                    Normal
                  </span>

                  <strong>
                    {normalCount}
                  </strong>
                </div>

                <div className="priority-card span-two">
                  <span>
                    Urgent Rate
                  </span>

                  <strong>
                    {pct(
                      urgentCount /
                        total
                    )}
                    %
                  </strong>
                </div>
              </div>
            )}
          </Panel>
        </div>
      </section>
    );
  };

  const renderStatus = () => (
    <Panel
      label="System"
      title="API & model health"
      chip={
        <button
          className="secondary-btn"
          onClick={
            checkHealth
          }
          disabled={
            healthLoading
          }
        >
          {healthLoading
            ? "Checking..."
            : "Refresh"}
        </button>
      }
    >
      {healthError && (
        <div className="error-message">
          {healthError}
        </div>
      )}

      <div className="stats-grid status-stats">
        <Stat
          label="API Status"
          value={
            online
              ? "Online"
              : "Offline"
          }
          note="Public /health"
        />

        <Stat
          label="Model"
          value={
            health?.model_version ||
            "—"
          }
          note="Active version"
        />

        <Stat
          label="Model Loaded"
          value={
            health
              ? health.model_loaded
                ? "Yes"
                : "No"
              : "—"
          }
          note="Runtime availability"
        />

        <Stat
          label="Authentication"
          value={
            API_KEY
              ? "Enabled"
              : "No key"
          }
          note="Protected endpoints"
        />
      </div>

      <div className="endpoint-grid">
        {[
          [
            "Single Prediction",
            "POST /predict",
          ],
          [
            "Batch Prediction",
            "POST /predict/batch",
          ],
          [
            "Async Jobs",
            "POST /batch/jobs",
          ],
          [
            "Health",
            "GET /health",
          ],
        ].map(
          ([
            label,
            endpoint,
          ]) => (
            <div
              className="endpoint-card"
              key={label}
            >
              <span>
                {label}
              </span>

              <strong>
                {endpoint}
              </strong>
            </div>
          )
        )}
      </div>
    </Panel>
  );

  const title =
    NAV.find(
      ([id]) =>
        id === activeView
    )?.[2] || "RouteIQ";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">
            <Icon
              name="route"
              size={21}
            />
          </div>

          <div>
            <h2>
              RouteIQ
            </h2>

            <p>
              Support Intelligence
            </p>
          </div>
        </div>

        <nav className="nav-menu">
          {NAV.map(
            ([
              id,
              label,
            ]) => (
              <button
                key={id}
                className={`nav-item ${
                  activeView ===
                  id
                    ? "active"
                    : ""
                }`}
                onClick={() =>
                  setActiveView(
                    id
                  )
                }
              >
                <Icon
                  name={id}
                  size={17}
                />

                {label}
              </button>
            )
          )}
        </nav>

        <div className="sidebar-footer">
          <div className="api-status">
            <span
              className={`status-dot ${
                online
                  ? "on"
                  : "off"
              }`}
            />

            <div>
              <strong>
                {online
                  ? "API Online"
                  : "API Offline"}
              </strong>

              <p>
                {health?.model_version
                  ? `Model ${health.model_version}`
                  : "Connection unavailable"}
              </p>
            </div>
          </div>
        </div>
      </aside>

      <main className="main-content">
        {activeView !==
          "dashboard" && (
          <header className="topbar">
            <div>
              <p className="eyebrow">
                TensorForge 2.0
              </p>

              <h1>
                {title}
              </h1>

              <p className="subtitle">
                Multilingual customer
                support classification
                and team routing
              </p>
            </div>

            <div
              className={`live-badge ${
                online
                  ? "on"
                  : "off"
              }`}
            >
              <span
                className={`status-dot ${
                  online
                    ? "on"
                    : "off"
                }`}
              />

              {online
                ? "Live System"
                : "API Offline"}
            </div>
          </header>
        )}

        <div
          className="view"
          key={activeView}
        >
          {activeView ===
          "dashboard"
            ? renderDashboard()
            : activeView ===
              "single"
            ? renderSingle()
            : activeView ===
              "batch"
            ? renderBatch()
            : activeView ===
              "analytics"
            ? renderAnalytics()
            : renderStatus()}
        </div>
      </main>
    </div>
  );
}

export default App;