import express from "express";
import path from "path";
import { fileURLToPath } from "url";

const app = express();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

app.use(express.json());

const API_URL =
  process.env.API_URL ||
  "https://tensorforge2-mvp-production.up.railway.app";

const API_KEY = process.env.API_KEY;

async function proxyRequest(req, res, endpoint) {
  try {
    const response = await fetch(`${API_URL}${endpoint}`, {
      method: req.method,
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
      },
      body:
        req.method === "GET"
          ? undefined
          : JSON.stringify(req.body),
    });

    const data = await response.json();

    res.status(response.status).json(data);
  } catch (error) {
    console.error("Proxy error:", error);

    res.status(500).json({
      error: {
        code: "proxy_error",
        message: "Unable to reach RouteIQ API.",
      },
    });
  }
}

// Public backend health check
app.get("/api/health", async (req, res) => {
  try {
    const response = await fetch(`${API_URL}/health`);

    const data = await response.json();

    res.status(response.status).json(data);
  } catch (error) {
    console.error("Health proxy error:", error);

    res.status(500).json({
      status: "error",
      model_version: null,
      model_loaded: false,
    });
  }
});

// Single prediction
app.post("/api/predict", async (req, res) => {
  await proxyRequest(req, res, "/predict");
});

// Synchronous batch prediction
app.post("/api/predict/batch", async (req, res) => {
  await proxyRequest(req, res, "/predict/batch");
});

// Async job creation
app.post("/api/batch/jobs", async (req, res) => {
  await proxyRequest(req, res, "/batch/jobs");
});

// Async job status
app.get("/api/batch/jobs/:jobId", async (req, res) => {
  await proxyRequest(
    req,
    res,
    `/batch/jobs/${encodeURIComponent(req.params.jobId)}`
  );
});

// Async job results
app.get("/api/batch/jobs/:jobId/results", async (req, res) => {
  const query = new URLSearchParams();

  if (req.query.offset) {
    query.set("offset", req.query.offset);
  }

  if (req.query.limit) {
    query.set("limit", req.query.limit);
  }

  const suffix = query.toString()
    ? `?${query.toString()}`
    : "";

  await proxyRequest(
    req,
    res,
    `/batch/jobs/${encodeURIComponent(
      req.params.jobId
    )}/results${suffix}`
  );
});

// Serve built Vite frontend
app.use(
  express.static(
    path.join(__dirname, "dist")
  )
);

// React SPA fallback for Express 5
app.get("/{*splat}", (req, res) => {
  res.sendFile(
    path.join(
      __dirname,
      "dist",
      "index.html"
    )
  );
});

const port = process.env.PORT || 3000;

app.listen(
  port,
  "0.0.0.0",
  () => {
    console.log(
      `RouteIQ frontend running on port ${port}`
    );
    console.log(
      `Backend API: ${API_URL}`
    );
  }
);