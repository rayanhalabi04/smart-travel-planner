## Agent With Three Tools

The `/api/agent/run` endpoint now executes a LangGraph-based travel agent workflow with three allowlisted tools:

1. `destination_search` (RAG destination knowledge retrieval)
2. `classify_style` (trained ML travel-style classifier)
3. `weather` (live weather conditions)

### Tool Safety And Validation

- Tool execution is restricted to an explicit allowlist in `app/tools/registry.py`.
- Unknown tool names are refused and never executed.
- Every tool call validates arguments through a dedicated Pydantic schema before running.
- Validation failures and runtime failures are handled gracefully and logged.

### Persistence

- Each tool call is persisted to `tool_logs` with:
  - `tool_input`
  - `tool_output`
  - `status`
  - `error_message` (when failed)
- Agent runs are persisted in `agent_runs`.

### Tracing (LangSmith-Compatible)

The LangGraph run supports tracing when LangSmith/LangChain tracing env vars are set.

Typical env vars:

- `LANGSMITH_TRACING=true` or `LANGCHAIN_TRACING_V2=true`
- `LANGSMITH_API_KEY=...`
- `LANGSMITH_PROJECT=...` (optional)

Add a multi-tool trace screenshot after running an end-to-end demo.

## Two-Model Routing

- The agent now routes mechanical work (preference extraction + RAG query rewrite) to a cheaper Gemini model.
- Final recommendation synthesis is routed to a stronger Gemini model.
- Token usage and estimated cost are logged per LLM step and persisted on each `agent_runs` row.
- The final cost table/screenshot for one full query will be completed later.
