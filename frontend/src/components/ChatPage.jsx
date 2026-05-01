import { useEffect, useMemo, useRef, useState } from "react";
import { getRunTools, runAgent, UnauthorizedError } from "../api";
import ChatMessage from "./ChatMessage";
import ToolLogsPanel from "./ToolLogsPanel";

const PROMPT_CHIPS = [
  "I want a luxury trip to Dubai with warm weather and rooftop dining.",
  "I want a family trip to Orlando with activities for young kids.",
  "I want a budget cultural trip with museums and local food.",
];

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function createId(prefix) {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
}

function ChatPage({ token, onLogout, onUnauthorized }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [chatError, setChatError] = useState("");
  const [activeRunId, setActiveRunId] = useState(null);
  const [toolLogs, setToolLogs] = useState([]);
  const [toolsLoading, setToolsLoading] = useState(false);
  const [toolsError, setToolsError] = useState("");
  const chatViewportRef = useRef(null);

  useEffect(() => {
    if (!chatViewportRef.current) {
      return;
    }
    chatViewportRef.current.scrollTop = chatViewportRef.current.scrollHeight;
  }, [messages, isSubmitting]);

  const canSend = useMemo(() => input.trim().length > 0 && !isSubmitting, [input, isSubmitting]);

  const handleUnauthorized = () => {
    onUnauthorized();
  };

  const streamAssistantText = async (messageId, fullText) => {
    const safeText = fullText || "I could not generate a response this time.";
    const chunkSize = Math.max(2, Math.floor(safeText.length / 60));
    let cursor = 0;

    while (cursor < safeText.length) {
      cursor = Math.min(safeText.length, cursor + chunkSize);
      const next = safeText.slice(0, cursor);
      setMessages((current) =>
        current.map((item) => (item.id === messageId ? { ...item, text: next } : item)),
      );
      await wait(16);
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const prompt = input.trim();
    if (!prompt || isSubmitting) {
      return;
    }

    setInput("");
    setChatError("");
    setToolsError("");
    setIsSubmitting(true);

    setMessages((current) => [...current, { id: createId("user"), role: "user", text: prompt }]);

    try {
      const runResponse = await runAgent(prompt, token);
      const runId = runResponse?.id || null;
      const answer = runResponse?.output_text || "No answer returned by the agent.";
      const assistantMessageId = createId("assistant");

      setActiveRunId(runId);
      setToolLogs([]);
      setMessages((current) => [
        ...current,
        {
          id: assistantMessageId,
          role: "assistant",
          text: "",
          runId,
        },
      ]);

      let toolsPromise = null;
      if (runId) {
        setToolsLoading(true);
        toolsPromise = getRunTools(runId, token);
      } else {
        setToolsLoading(false);
      }

      await streamAssistantText(assistantMessageId, answer);

      if (toolsPromise) {
        try {
          const logs = await toolsPromise;
          setToolLogs(Array.isArray(logs) ? logs : []);
        } catch (error) {
          if (error instanceof UnauthorizedError) {
            handleUnauthorized();
            return;
          }
          setToolsError(error instanceof Error ? error.message : "Unable to load tool logs.");
          setToolLogs([]);
        } finally {
          setToolsLoading(false);
        }
      }
    } catch (error) {
      if (error instanceof UnauthorizedError) {
        handleUnauthorized();
        return;
      }

      const message =
        error instanceof Error ? error.message : "Something went wrong while calling the agent.";
      setChatError(message);
      setMessages((current) => [
        ...current,
        {
          id: createId("assistant_error"),
          role: "assistant",
          text: `I ran into a problem: ${message}`,
        },
      ]);
      setToolsLoading(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleComposerKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (canSend) {
        event.currentTarget.form?.requestSubmit();
      }
    }
  };

  return (
    <main className="planner-layout">
      <section className="chat-panel card">
        <header className="chat-header">
          <div>
            <p className="brand-kicker">Smart Travel Planner</p>
            <h1>Trip Assistant</h1>
            <p className="muted-text">Ask for destinations, style fit, and weather-aware ideas.</p>
          </div>
          <button className="secondary-button" onClick={onLogout} type="button">
            Logout
          </button>
        </header>

        {chatError ? <div className="error-banner">{chatError}</div> : null}

        <div className="chat-viewport" ref={chatViewportRef}>
          {messages.length === 0 ? (
            <div className="chat-empty">
              <h2>Start your next trip plan</h2>
              <p>
                Share your destination preferences, travel style, and budget. The assistant will run
                tools and return a personalized recommendation.
              </p>
            </div>
          ) : (
            messages.map((message) => (
              <ChatMessage
                key={message.id}
                role={message.role}
                text={message.text}
                runId={message.runId}
              />
            ))
          )}

          {isSubmitting ? (
            <article className="message-row message-assistant">
              <div className="message-bubble bubble-assistant">
                <p className="typing-dots">
                  Agent is planning<span>.</span>
                  <span>.</span>
                  <span>.</span>
                </p>
              </div>
            </article>
          ) : null}
        </div>

        <div className="chips-row">
          {PROMPT_CHIPS.map((chip) => (
            <button
              key={chip}
              type="button"
              className="prompt-chip"
              onClick={() => setInput(chip)}
              disabled={isSubmitting}
            >
              {chip}
            </button>
          ))}
        </div>

        <form className="chat-composer" onSubmit={handleSubmit}>
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleComposerKeyDown}
            placeholder="Example: Plan a 5-day luxury trip to Dubai with warm weather and art experiences."
            rows={3}
            disabled={isSubmitting}
          />
          <button className="primary-button composer-button" type="submit" disabled={!canSend}>
            {isSubmitting ? "Planning..." : "Send Request"}
          </button>
        </form>
      </section>

      <ToolLogsPanel runId={activeRunId} logs={toolLogs} loading={toolsLoading} error={toolsError} />
    </main>
  );
}

export default ChatPage;
