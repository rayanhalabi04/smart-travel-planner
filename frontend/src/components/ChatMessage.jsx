function ChatMessage({ role, text, runId }) {
  const isUser = role === "user";

  return (
    <article className={`message-row ${isUser ? "message-user" : "message-assistant"}`}>
      <div className={`message-bubble ${isUser ? "bubble-user" : "bubble-assistant"}`}>
        {!isUser && runId ? <p className="run-id-label">Run #{runId}</p> : null}
        <p>{text}</p>
      </div>
    </article>
  );
}

export default ChatMessage;
