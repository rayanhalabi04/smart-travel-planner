const TOOL_LABELS = {
  destination_search: "Destination Search",
  classify_style: "Classify Style",
  weather: "Weather",
};

function prettyToolName(name) {
  if (TOOL_LABELS[name]) {
    return TOOL_LABELS[name];
  }
  return name
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function summarizeEntries(payload) {
  if (!payload || typeof payload !== "object") {
    return [];
  }

  return Object.entries(payload)
    .slice(0, 4)
    .map(([key, value]) => {
      if (value === null || value === undefined) {
        return [key, "none"];
      }
      if (typeof value === "string") {
        return [key, value.length > 120 ? `${value.slice(0, 117)}...` : value];
      }
      if (typeof value === "number" || typeof value === "boolean") {
        return [key, String(value)];
      }
      if (Array.isArray(value)) {
        return [key, `${value.length} item(s)`];
      }
      if (typeof value === "object") {
        return [key, `${Object.keys(value).length} field(s)`];
      }
      return [key, String(value)];
    });
}

function summarizeOutput(payload, status, errorMessage) {
  if (status === "failed") {
    return errorMessage || "Tool execution failed.";
  }

  if (!payload || typeof payload !== "object") {
    return "No structured output returned.";
  }

  if (typeof payload.summary === "string") {
    return payload.summary;
  }

  const entries = Object.entries(payload);
  if (entries.length === 0) {
    return "Output is empty.";
  }

  return entries
    .slice(0, 3)
    .map(([key, value]) => {
      if (typeof value === "string") {
        return `${key}: ${value.slice(0, 80)}${value.length > 80 ? "..." : ""}`;
      }
      if (typeof value === "number" || typeof value === "boolean") {
        return `${key}: ${value}`;
      }
      if (Array.isArray(value)) {
        return `${key}: ${value.length} item(s)`;
      }
      if (value && typeof value === "object") {
        return `${key}: ${Object.keys(value).length} field(s)`;
      }
      return `${key}: none`;
    })
    .join(" • ");
}

function ToolLogsPanel({ runId, logs, loading, error }) {
  return (
    <aside className="tool-panel card">
      <header className="panel-header">
        <p className="panel-kicker">Tool Inspector</p>
        <h2>Agent Steps</h2>
        <p className="muted-text small-text">
          {runId ? `Inspecting run #${runId}` : "Run the agent to view tool activity"}
        </p>
      </header>

      {!runId ? (
        <div className="tool-empty">No run selected yet.</div>
      ) : null}

      {loading ? <div className="tool-loading">Loading tool logs...</div> : null}
      {error ? <div className="warning-banner">{error}</div> : null}

      {runId && !loading && logs.length === 0 ? (
        <div className="tool-empty">No tools recorded for this run.</div>
      ) : null}

      <div className="tool-list">
        {logs.map((log) => {
          const inputs = summarizeEntries(log.tool_input);
          const outputSummary = summarizeOutput(log.tool_output, log.status, log.error_message);
          const statusClass =
            log.status === "success"
              ? "status-success"
              : log.status === "failed"
                ? "status-failed"
                : "status-neutral";

          return (
            <article key={log.id} className="tool-card">
              <div className="tool-card-top">
                <h3>{prettyToolName(log.tool_name)}</h3>
                <span className={`status-badge ${statusClass}`}>{log.status}</span>
              </div>

              <div className="tool-section">
                <p className="tool-label">Key Inputs</p>
                {inputs.length > 0 ? (
                  <ul className="kv-list">
                    {inputs.map(([key, value]) => (
                      <li key={key}>
                        <span>{key}</span>
                        <strong>{value}</strong>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="muted-text small-text">No inputs captured.</p>
                )}
              </div>

              <div className="tool-section">
                <p className="tool-label">Output Summary</p>
                <p className="summary-text">{outputSummary}</p>
              </div>

              <details className="raw-details">
                <summary>Raw JSON</summary>
                <pre>
                  {JSON.stringify(
                    {
                      tool_input: log.tool_input,
                      tool_output: log.tool_output,
                      error_message: log.error_message,
                    },
                    null,
                    2,
                  )}
                </pre>
              </details>
            </article>
          );
        })}
      </div>
    </aside>
  );
}

export default ToolLogsPanel;
