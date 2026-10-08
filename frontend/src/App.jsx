import { useEffect, useMemo, useState } from "react";
import "./App.css";

const API_URL = (
  import.meta.env.VITE_API_URL || "http://localhost:8000"
).replace(/\/$/, "");

const API_KEY = import.meta.env.VITE_API_KEY || "";

const MODEL_VERSION = "v1.2";
const MAX_BATCH_SIZE = 100;

function App() {
  const [activeView, setActiveView] = useState("dashboard");

  // =========================================================
  // HEALTH
  // =========================================================

  const [health, setHealth] = useState(null);
  const [healthLoading, setHealthLoading] = useState(false);
  const [healthError, setHealthError] = useState("");

  // =========================================================
  // SINGLE TICKET
  // =========================================================

  const [channel, setChannel] = useState("email");
  const [subject, setSubject] = useState("");
  const [text, setText] = useState("");

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // =========================================================
  // BATCH
  // =========================================================

  const [batchText, setBatchText] = useState("");
  const [batchResults, setBatchResults] = useState([]);
  const [batchLoading, setBatchLoading] = useState(false);
  const [batchError, setBatchError] = useState("");

  // =========================================================
  // HELPERS
  // =========================================================

  const formatLabel = (value) => {
    if (!value) {
      return "None";
    }

    return String(value)
      .replaceAll("_", " ")
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  };

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

  // =========================================================
  // HEALTH CHECK
  // =========================================================

  const checkHealth = async () => {
    setHealthLoading(true);
    setHealthError("");

    try {
      const response = await fetch(`${API_URL}/health`);

      if (!response.ok) {
        throw new Error("Health check failed.");
      }

      const data = await response.json();

      setHealth(data);
    } catch (err) {
      setHealth(null);

      setHealthError(
        err.message || "Unable to reach API."
      );
    } finally {
      setHealthLoading(false);
    }
  };

  useEffect(() => {
    checkHealth();
  }, []);

  // =========================================================
  // SINGLE TICKET PREDICTION
  // =========================================================

  const analyzeTicket = async () => {
    if (!text.trim()) {
      setError("Ticket message is required.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch(
        `${API_URL}/predict`,
        {
          method: "POST",

          headers: getHeaders(),

          body: JSON.stringify({
            ticket_id: `WEB-${Date.now()}`,
            channel,
            subject: subject.trim(),
            text: text.trim(),
          }),
        }
      );

      if (!response.ok) {
        const message = await getErrorMessage(
          response,
          "Prediction failed."
        );

        throw new Error(message);
      }

      const data = await response.json();

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

  // =========================================================
  // BATCH
  // =========================================================

  const batchLines = useMemo(() => {
    return batchText
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
  }, [batchText]);

  const batchCount = batchLines.length;

  const analyzeBatch = async () => {
    if (batchCount === 0) {
      setBatchError(
        "Enter at least one ticket."
      );

      return;
    }

    if (batchCount > MAX_BATCH_SIZE) {
      setBatchError(
        `Maximum ${MAX_BATCH_SIZE} tickets are allowed for synchronous batch analysis.`
      );

      return;
    }

    setBatchLoading(true);
    setBatchError("");
    setBatchResults([]);

    try {
      const timestamp = Date.now();

      const tickets = batchLines.map(
        (line, index) => ({
          ticket_id: `BATCH-${timestamp}-${index + 1}`,
          channel: "email",
          subject: "",
          text: line,
        })
      );

      const response = await fetch(
        `${API_URL}/predict/batch`,
        {
          method: "POST",

          headers: getHeaders(),

          body: JSON.stringify({
            tickets,
          }),
        }
      );

      if (!response.ok) {
        const message = await getErrorMessage(
          response,
          "Batch prediction failed."
        );

        throw new Error(message);
      }

      const data = await response.json();

      if (Array.isArray(data)) {
        setBatchResults(data);
      } else {
        setBatchResults(
          data.predictions ||
            data.results ||
            []
        );
      }
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

  // =========================================================
  // VALUES
  // =========================================================

  const confidencePercent = result
    ? Math.round(
        (result.confidence || 0) * 100
      )
    : 0;

  const analytics = useMemo(() => {
    const total = batchResults.length;

    const urgentCount =
      batchResults.filter(
        (item) => item.is_urgent
      ).length;

    const normalCount =
      total - urgentCount;

    const avgConfidence =
      total > 0
        ? Math.round(
            (batchResults.reduce(
              (sum, item) =>
                sum +
                (item.confidence || 0),
              0
            ) /
              total) *
              100
          )
        : 0;

    const categoryCounts = {};

    batchResults.forEach((item) => {
      const category =
        item.category || "unknown";

      categoryCounts[category] =
        (categoryCounts[category] || 0) +
        1;
    });

    const categoryEntries =
      Object.entries(
        categoryCounts
      ).sort(
        (a, b) => b[1] - a[1]
      );

    return {
      total,
      urgentCount,
      normalCount,
      avgConfidence,
      categoryEntries,
    };
  }, [batchResults]);

  // =========================================================
  // SINGLE TICKET UI
  // =========================================================

  const renderSingleTicket = () => (
    <>
      <section className="workspace-grid">
        <div className="panel analyzer-panel">
          <div className="panel-header">
            <div>
              <p className="panel-label">
                Single Ticket Analyzer
              </p>

              <h2>
                Analyze a support request
              </h2>
            </div>

            <span className="panel-chip">
              Real-time inference
            </span>
          </div>

          <div className="form-grid">
            <div className="form-group">
              <label>Channel</label>

              <select
                value={channel}
                onChange={(e) =>
                  setChannel(e.target.value)
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
              <label>Subject</label>

              <input
                type="text"
                placeholder="Example: Duplicate payment"
                value={subject}
                onChange={(e) =>
                  setSubject(e.target.value)
                }
              />
            </div>

            <div className="form-group full-width">
              <label>
                Ticket message
              </label>

              <textarea
                rows="8"
                placeholder="Paste the customer support message here..."
                value={text}
                onChange={(e) =>
                  setText(e.target.value)
                }
              />
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
                  ? "Input ready"
                  : "Waiting for ticket"}
              </span>

              <small>
                {text.length} characters ·{" "}
                {channel}
              </small>
            </div>

            <div
              style={{
                display: "flex",
                gap: "10px",
                flexWrap: "wrap",
              }}
            >
              <button
                className="nav-item"
                onClick={clearSingle}
                type="button"
                disabled={loading}
              >
                Clear
              </button>

              <button
                className="analyze-btn"
                onClick={analyzeTicket}
                disabled={
                  loading ||
                  !text.trim()
                }
              >
                {loading
                  ? "Analyzing..."
                  : "Analyze Ticket"}
              </button>
            </div>
          </div>
        </div>

        <div className="panel result-panel">
          <div className="panel-header">
            <div>
              <p className="panel-label">
                Prediction Output
              </p>

              <h2>
                Routing decision
              </h2>
            </div>

            {result?.model_version && (
              <span className="panel-chip">
                Model{" "}
                {result.model_version}
              </span>
            )}
          </div>

          {!result ? (
            <div className="empty-result">
              <div className="result-icon">
                AI
              </div>

              <h3>
                {loading
                  ? "Running inference..."
                  : "Ready for analysis"}
              </h3>

              <p>
                {loading
                  ? "RouteIQ is processing the ticket using the trained machine-learning pipeline."
                  : "Enter a ticket and run the model to view category, urgency, confidence and assigned team."}
              </p>
            </div>
          ) : (
            <div className="prediction-result">
              <div className="prediction-main">
                <span className="result-label">
                  Primary Category
                </span>

                <h3>
                  {formatLabel(
                    result.category
                  )}
                </h3>
              </div>

              <div className="prediction-grid">
                <div className="prediction-card">
                  <span>
                    Assigned Team
                  </span>

                  <strong>
                    {result.team || "—"}
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
                    Secondary Category
                  </span>

                  <strong>
                    {formatLabel(
                      result.secondary_category
                    )}
                  </strong>
                </div>

                <div className="prediction-card">
                  <span>
                    Model Version
                  </span>

                  <strong>
                    {result.model_version ||
                      MODEL_VERSION}
                  </strong>
                </div>
              </div>

              <div className="confidence-box">
                <div className="confidence-header">
                  <span>
                    Confidence Indicator
                  </span>

                  <strong>
                    {confidencePercent}%
                  </strong>
                </div>

                <div className="confidence-track">
                  <div
                    className="confidence-fill"
                    style={{
                      width: `${confidencePercent}%`,
                    }}
                  />
                </div>

                <small>
                  Decision-score based
                  indicator; not a calibrated
                  probability.
                </small>
              </div>

              {result.ticket_id && (
                <div className="ticket-reference">
                  Ticket ID:{" "}
                  {result.ticket_id}
                </div>
              )}
            </div>
          )}

          <div className="result-metadata">
            <div>
              <span>Endpoint</span>
              <strong>
                /predict
              </strong>
            </div>

            <div>
              <span>Model</span>

              <strong>
                {result?.model_version ||
                  health?.model_version ||
                  MODEL_VERSION}
              </strong>
            </div>
          </div>
        </div>
      </section>

      <section className="bottom-grid">
        <div className="panel compact-panel">
          <p className="panel-label">
            Pipeline
          </p>

          <h3>
            Inference workflow
          </h3>

          <div className="pipeline">
            <span>Ticket Input</span>
            <span>→</span>
            <span>Text Features</span>
            <span>→</span>
            <span>ML Models</span>
            <span>→</span>
            <span>Team Routing</span>
          </div>
        </div>

        <div className="panel compact-panel">
          <p className="panel-label">
            System
          </p>

          <h3>
            Competition-ready
            architecture
          </h3>

          <p className="compact-text">
            React frontend connected
            to a FastAPI inference
            service with authenticated
            prediction and batch
            endpoints.
          </p>
        </div>
      </section>
    </>
  );

  // =========================================================
  // BATCH UI
  // =========================================================

  const renderBatchAnalysis = () => (
    <section>
      <div className="panel">
        <div className="panel-header">
          <div>
            <p className="panel-label">
              Batch Analysis
            </p>

            <h2>
              Analyze multiple
              support tickets
            </h2>
          </div>

          <span className="panel-chip">
            /predict/batch
          </span>
        </div>

        <div className="form-group">
          <label>
            Tickets — one ticket per
            line
          </label>

          <textarea
            rows="10"
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
              Maximum{" "}
              {MAX_BATCH_SIZE} tickets
              per synchronous request
            </small>
          </div>

          <div
            style={{
              display: "flex",
              gap: "10px",
              flexWrap: "wrap",
            }}
          >
            <button
              className="nav-item"
              onClick={clearBatch}
              type="button"
              disabled={batchLoading}
            >
              Clear
            </button>

            <button
              className="analyze-btn"
              onClick={analyzeBatch}
              disabled={
                batchLoading ||
                batchCount === 0
              }
            >
              {batchLoading
                ? "Analyzing Batch..."
                : "Run Batch Analysis"}
            </button>
          </div>
        </div>
      </div>

      <div
        className="panel"
        style={{
          marginTop: "18px",
        }}
      >
        <div className="panel-header">
          <div>
            <p className="panel-label">
              Batch Results
            </p>

            <h2>
              Routing predictions
            </h2>
          </div>

          {batchResults.length > 0 && (
            <span className="panel-chip">
              {batchResults.length}{" "}
              predictions
            </span>
          )}
        </div>

        {batchResults.length === 0 ? (
          <div className="empty-result">
            <div className="result-icon">
              AI
            </div>

            <h3>
              {batchLoading
                ? "Processing batch..."
                : "No batch results yet"}
            </h3>

            <p>
              Enter multiple tickets
              above and run batch
              analysis to view routing
              decisions.
            </p>
          </div>
        ) : (
          <div
            style={{
              overflowX: "auto",
            }}
          >
            <table
              style={{
                width: "100%",
                borderCollapse:
                  "collapse",
                minWidth: "850px",
              }}
            >
              <thead>
                <tr
                  style={{
                    textAlign: "left",
                    color: "#7f8ea3",
                    fontSize: "11px",
                  }}
                >
                  <th
                    style={{
                      padding: "12px",
                    }}
                  >
                    #
                  </th>

                  <th
                    style={{
                      padding: "12px",
                    }}
                  >
                    Category
                  </th>

                  <th
                    style={{
                      padding: "12px",
                    }}
                  >
                    Secondary
                  </th>

                  <th
                    style={{
                      padding: "12px",
                    }}
                  >
                    Team
                  </th>

                  <th
                    style={{
                      padding: "12px",
                    }}
                  >
                    Urgency
                  </th>

                  <th
                    style={{
                      padding: "12px",
                    }}
                  >
                    Confidence
                  </th>

                  <th
                    style={{
                      padding: "12px",
                    }}
                  >
                    Model
                  </th>
                </tr>
              </thead>

              <tbody>
                {batchResults.map(
                  (item, index) => (
                    <tr
                      key={
                        item.ticket_id ||
                        index
                      }
                      style={{
                        borderTop:
                          "1px solid rgba(148,163,184,0.08)",
                        fontSize:
                          "12px",
                      }}
                    >
                      <td
                        style={{
                          padding:
                            "14px 12px",
                          color:
                            "#64748b",
                        }}
                      >
                        {index + 1}
                      </td>

                      <td
                        style={{
                          padding:
                            "14px 12px",
                          fontWeight:
                            700,
                        }}
                      >
                        {formatLabel(
                          item.category
                        )}
                      </td>

                      <td
                        style={{
                          padding:
                            "14px 12px",
                        }}
                      >
                        {formatLabel(
                          item.secondary_category
                        )}
                      </td>

                      <td
                        style={{
                          padding:
                            "14px 12px",
                        }}
                      >
                        {item.team ||
                          "—"}
                      </td>

                      <td
                        style={{
                          padding:
                            "14px 12px",
                        }}
                      >
                        <span
                          className={
                            item.is_urgent
                              ? "urgent-text"
                              : "normal-text"
                          }
                        >
                          {item.is_urgent
                            ? "Urgent"
                            : "Normal"}
                        </span>
                      </td>

                      <td
                        style={{
                          padding:
                            "14px 12px",
                        }}
                      >
                        {Math.round(
                          (item.confidence ||
                            0) *
                            100
                        )}
                        %
                      </td>

                      <td
                        style={{
                          padding:
                            "14px 12px",
                        }}
                      >
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
      </div>
    </section>
  );

  // =========================================================
  // ANALYTICS
  // =========================================================

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
          <div className="stat-card">
            <span>
              Analyzed Tickets
            </span>

            <strong>
              {total}
            </strong>

            <small>
              Current session batch
              data
            </small>
          </div>

          <div className="stat-card">
            <span>
              Urgent Tickets
            </span>

            <strong>
              {urgentCount}
            </strong>

            <small>
              Priority routing
              detected
            </small>
          </div>

          <div className="stat-card">
            <span>
              Normal Tickets
            </span>

            <strong>
              {normalCount}
            </strong>

            <small>
              Standard support flow
            </small>
          </div>

          <div className="stat-card">
            <span>
              Average Confidence
            </span>

            <strong>
              {avgConfidence}%
            </strong>

            <small>
              Decision-score
              indicator
            </small>
          </div>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns:
              "repeat(auto-fit, minmax(300px, 1fr))",
            gap: "18px",
          }}
        >
          <div className="panel">
            <div className="panel-header">
              <div>
                <p className="panel-label">
                  Category Distribution
                </p>

                <h2>
                  Ticket classification
                  summary
                </h2>
              </div>
            </div>

            {categoryEntries.length ===
            0 ? (
              <div className="empty-result">
                <div className="result-icon">
                  AI
                </div>

                <h3>
                  No analytics data yet
                </h3>

                <p>
                  Run Batch Analysis
                  first. RouteIQ will
                  summarize the
                  predictions here.
                </p>
              </div>
            ) : (
              <div
                style={{
                  display: "flex",
                  flexDirection:
                    "column",
                  gap: "14px",
                }}
              >
                {categoryEntries.map(
                  ([
                    category,
                    count,
                  ]) => {
                    const percentage =
                      Math.round(
                        (count /
                          total) *
                          100
                      );

                    return (
                      <div
                        key={
                          category
                        }
                      >
                        <div
                          style={{
                            display:
                              "flex",
                            justifyContent:
                              "space-between",
                            marginBottom:
                              "7px",
                            fontSize:
                              "12px",
                            gap: "10px",
                          }}
                        >
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

                        <div className="confidence-track">
                          <div
                            className="confidence-fill"
                            style={{
                              width: `${percentage}%`,
                            }}
                          />
                        </div>
                      </div>
                    );
                  }
                )}
              </div>
            )}
          </div>

          <div className="panel">
            <div className="panel-header">
              <div>
                <p className="panel-label">
                  Priority Overview
                </p>

                <h2>
                  Urgency distribution
                </h2>
              </div>
            </div>

            {total === 0 ? (
              <div className="empty-result">
                <div className="result-icon">
                  AI
                </div>

                <h3>
                  Waiting for
                  predictions
                </h3>

                <p>
                  Batch prediction
                  results will be used
                  to calculate urgency
                  analytics.
                </p>
              </div>
            ) : (
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns:
                    "repeat(2, minmax(0, 1fr))",
                  gap: "12px",
                }}
              >
                <div className="prediction-card">
                  <span>
                    Urgent
                  </span>

                  <strong className="urgent-text">
                    {urgentCount}
                  </strong>
                </div>

                <div className="prediction-card">
                  <span>
                    Normal
                  </span>

                  <strong className="normal-text">
                    {normalCount}
                  </strong>
                </div>

                <div
                  className="prediction-card"
                  style={{
                    gridColumn:
                      "1 / -1",
                  }}
                >
                  <span>
                    Urgent Rate
                  </span>

                  <strong>
                    {Math.round(
                      (urgentCount /
                        total) *
                        100
                    )}
                    %
                  </strong>
                </div>

                <div
                  className="prediction-card"
                  style={{
                    gridColumn:
                      "1 / -1",
                  }}
                >
                  <span>
                    Average Confidence
                  </span>

                  <strong>
                    {avgConfidence}%
                  </strong>
                </div>
              </div>
            )}
          </div>
        </div>
      </section>
    );
  };

  // =========================================================
  // SYSTEM STATUS
  // =========================================================

  const renderSystemStatus = () => (
    <section>
      <div className="panel">
        <div className="panel-header">
          <div>
            <p className="panel-label">
              System Status
            </p>

            <h2>
              API and model health
            </h2>
          </div>

          <button
            className="analyze-btn"
            onClick={checkHealth}
            disabled={healthLoading}
          >
            {healthLoading
              ? "Checking..."
              : "Run Health Check"}
          </button>
        </div>

        {healthError && (
          <div className="error-message">
            {healthError}
          </div>
        )}

        <div className="stats-grid">
          <div className="stat-card">
            <span>
              API Status
            </span>

            <strong>
              {health?.status === "ok"
                ? "Online"
                : "Offline"}
            </strong>

            <small>
              Public /health endpoint
            </small>
          </div>

          <div className="stat-card">
            <span>
              Model Version
            </span>

            <strong>
              {health?.model_version ||
                "—"}
            </strong>

            <small>
              Active inference model
            </small>
          </div>

          <div className="stat-card">
            <span>
              Model Loaded
            </span>

            <strong>
              {health
                ? health.model_loaded
                  ? "Yes"
                  : "No"
                : "—"}
            </strong>

            <small>
              Runtime model
              availability
            </small>
          </div>

          <div className="stat-card">
            <span>
              Authentication
            </span>

            <strong>
              Enabled
            </strong>

            <small>
              Protected prediction
              endpoints
            </small>
          </div>
        </div>

        <div
          style={{
            marginTop: "18px",
            display: "grid",
            gridTemplateColumns:
              "repeat(auto-fit, minmax(220px, 1fr))",
            gap: "12px",
          }}
        >
          <div className="prediction-card">
            <span>
              Single Prediction
            </span>

            <strong>
              POST /predict
            </strong>
          </div>

          <div className="prediction-card">
            <span>
              Batch Prediction
            </span>

            <strong>
              POST /predict/batch
            </strong>
          </div>

          <div className="prediction-card">
            <span>
              Async Batch Jobs
            </span>

            <strong>
              POST /batch/jobs
            </strong>
          </div>

          <div className="prediction-card">
            <span>
              Health
            </span>

            <strong>
              GET /health
            </strong>
          </div>
        </div>
      </div>
    </section>
  );

  // =========================================================
  // PAGE TITLE
  // =========================================================

  const pageTitle = () => {
    if (activeView === "batch") {
      return "Batch Ticket Analysis";
    }

    if (activeView === "analytics") {
      return "Ticket Analytics";
    }

    if (activeView === "status") {
      return "System Status";
    }

    return "Support Routing Dashboard";
  };

  // =========================================================
  // UI
  // =========================================================

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">
            R
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
          <button
            className={`nav-item ${
              activeView === "dashboard"
                ? "active"
                : ""
            }`}
            onClick={() =>
              setActiveView(
                "dashboard"
              )
            }
          >
            Dashboard
          </button>

          <button
            className={`nav-item ${
              activeView === "single"
                ? "active"
                : ""
            }`}
            onClick={() =>
              setActiveView(
                "single"
              )
            }
          >
            Single Ticket
          </button>

          <button
            className={`nav-item ${
              activeView === "batch"
                ? "active"
                : ""
            }`}
            onClick={() =>
              setActiveView(
                "batch"
              )
            }
          >
            Batch Analysis
          </button>

          <button
            className={`nav-item ${
              activeView ===
              "analytics"
                ? "active"
                : ""
            }`}
            onClick={() =>
              setActiveView(
                "analytics"
              )
            }
          >
            Analytics
          </button>

          <button
            className={`nav-item ${
              activeView === "status"
                ? "active"
                : ""
            }`}
            onClick={() =>
              setActiveView(
                "status"
              )
            }
          >
            System Status
          </button>
        </nav>

        <div className="sidebar-footer">
          <div className="api-status">
            <span
              className="status-dot"
              style={{
                background:
                  health?.status ===
                  "ok"
                    ? "#34d399"
                    : "#f87171",

                boxShadow:
                  health?.status ===
                  "ok"
                    ? "0 0 0 5px rgba(52, 211, 153, 0.1)"
                    : "0 0 0 5px rgba(248, 113, 113, 0.1)",
              }}
            />

            <div>
              <strong>
                {health?.status ===
                "ok"
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
        <header className="topbar">
          <div>
            <p className="eyebrow">
              TensorForge 2.0 · Phase 2
            </p>

            <h1>
              {pageTitle()}
            </h1>

            <p className="subtitle">
              Intelligent
              multilingual ticket
              classification and team
              routing
            </p>
          </div>

          <div
            className="topbar-badge"
            style={{
              color:
                health?.status ===
                "ok"
                  ? "#a7f3d0"
                  : "#fecaca",

              borderColor:
                health?.status ===
                "ok"
                  ? "rgba(52,211,153,0.15)"
                  : "rgba(248,113,113,0.2)",

              background:
                health?.status ===
                "ok"
                  ? "rgba(52,211,153,0.08)"
                  : "rgba(248,113,113,0.08)",
            }}
          >
            <span
              className="pulse"
              style={{
                background:
                  health?.status ===
                  "ok"
                    ? "#34d399"
                    : "#f87171",
              }}
            />

            {health?.status === "ok"
              ? "Live System"
              : "API Offline"}
          </div>
        </header>

        {activeView !==
          "analytics" &&
          activeView !==
            "status" && (
            <section className="stats-grid">
              <div className="stat-card">
                <span>
                  Category Model
                </span>

                <strong>
                  88.1%
                </strong>

                <small>
                  Validation accuracy
                </small>
              </div>

              <div className="stat-card">
                <span>
                  Primary Categories
                </span>

                <strong>
                  11
                </strong>

                <small>
                  Automated routing
                  classes
                </small>
              </div>

              <div className="stat-card">
                <span>
                  Urgency Detection
                </span>

                <strong>
                  97.1%
                </strong>

                <small>
                  Validation accuracy
                </small>
              </div>

              <div className="stat-card">
                <span>
                  API
                </span>

                <strong>
                  {health?.status ===
                  "ok"
                    ? "Healthy"
                    : "Offline"}
                </strong>

                <small>
                  FastAPI inference
                  service
                </small>
              </div>
            </section>
          )}

        {activeView === "batch"
          ? renderBatchAnalysis()
          : activeView ===
              "analytics"
          ? renderAnalytics()
          : activeView ===
              "status"
          ? renderSystemStatus()
          : renderSingleTicket()}
      </main>
    </div>
  );
}

export default App;