import { useEffect, useRef, useState } from "react";
import { api } from "./api.js";

const suggestedQuestions = [
  "What are today's total sales?",
  "Compare this month's sales with last month.",
  "Which food items sell the most?",
  "Which ingredients are running low?",
  "Predict revenue and profit until March 2027.",
  "Why have sales decreased?",
];

function renderInline(text) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, index) =>
    part.startsWith("**") && part.endsWith("**")
      ? <strong key={index}>{part.slice(2, -2)}</strong>
      : part
  );
}

function renderAnswer(content) {
  const lines = content.split(/\r?\n/);
  const blocks = [];
  let index = 0;
  while (index < lines.length) {
    if (!lines[index].trim()) {
      index += 1;
      continue;
    }
    if (lines[index].includes("|") && index + 1 < lines.length && /^\s*\|?\s*:?-{3,}/.test(lines[index + 1])) {
      const cells = (line) => line.split("|").map((cell) => cell.trim()).filter((cell, cellIndex, all) =>
        !(cellIndex === 0 && !cell) && !(cellIndex === all.length - 1 && !cell)
      );
      const headers = cells(lines[index]);
      index += 2;
      const rows = [];
      while (index < lines.length && lines[index].includes("|")) {
        rows.push(cells(lines[index]));
        index += 1;
      }
      blocks.push(
        <div className="admin-chat-table-wrap" key={`table-${index}`}>
          <table><thead><tr>{headers.map((cell, cellIndex) => <th key={cellIndex}>{renderInline(cell)}</th>)}</tr></thead>
            <tbody>{rows.map((row, rowIndex) => <tr key={rowIndex}>{headers.map((_, cellIndex) => <td key={cellIndex}>{renderInline(row[cellIndex] || "")}</td>)}</tr>)}</tbody>
          </table>
        </div>
      );
      continue;
    }
    const listMatch = lines[index].match(/^\s*(?:[-*]|\d+\.)\s+(.+)/);
    if (listMatch) {
      const items = [];
      while (index < lines.length) {
        const match = lines[index].match(/^\s*(?:[-*]|\d+\.)\s+(.+)/);
        if (!match) break;
        items.push(match[1]);
        index += 1;
      }
      blocks.push(<ul key={`list-${index}`}>{items.map((item, itemIndex) => <li key={itemIndex}>{renderInline(item)}</li>)}</ul>);
      continue;
    }
    const paragraph = [];
    while (index < lines.length && lines[index].trim() && !lines[index].includes("|")) {
      paragraph.push(lines[index].trim());
      index += 1;
    }
    if (paragraph.length) blocks.push(<p key={`paragraph-${index}`}>{renderInline(paragraph.join(" "))}</p>);
  }
  return blocks;
}

function formatTime(value) {
  return new Date(value).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
}

export default function AdminChat({ user }) {
  const storageKey = `restaurant-admin-chat-${user.id}`;
  const [messages, setMessages] = useState(() => {
    try {
      const saved = JSON.parse(window.localStorage.getItem(storageKey) || "[]");
      return Array.isArray(saved) ? saved.slice(-50) : [];
    } catch {
      return [];
    }
  });
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sessionId, setSessionId] = useState(0);
  const endRef = useRef(null);
  const requestController = useRef(null);

  useEffect(() => {
    try {
      window.localStorage.setItem(storageKey, JSON.stringify(messages.slice(-50)));
    } catch {
      setError("Chat history could not be saved in this browser.");
    }
  }, [messages, storageKey]);

  useEffect(() => () => requestController.current?.abort(), []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, busy]);

  async function sendMessage(text = question) {
    const content = text.trim();
    if (!content || busy) return;
    const nextMessages = [...messages, { role: "user", content, timestamp: new Date().toISOString() }];
    setMessages(nextMessages);
    setQuestion("");
    setError("");
    setBusy(true);
    const controller = new AbortController();
    requestController.current = controller;
    try {
      const response = await api("/admin/chat", {
        method: "POST",
        signal: controller.signal,
        body: JSON.stringify({
          messages: nextMessages.slice(-20).map(({ role, content: messageContent }) => ({ role, content: messageContent })),
        }),
      });
      setMessages((current) => [...current, {
        role: "assistant",
        content: response.answer,
        timestamp: response.timestamp || new Date().toISOString(),
        tools: response.tools_used || [],
      }].slice(-50));
    } catch (requestError) {
      setError(requestError.name === "AbortError" ? "Request stopped." : requestError.message);
    } finally {
      if (requestController.current === controller) requestController.current = null;
      setBusy(false);
    }
  }

  function stopRequest() {
    requestController.current?.abort();
  }

  function clearHistory() {
    if (busy) return;
    setMessages([]);
    setError("");
    setSessionId((current) => current + 1);
  }

  return (
    <section className="admin-chat-page" key={sessionId}>
      <header className="admin-chat-heading">
        <div><div className="eyebrow">PRIVATE BUSINESS ASSISTANT</div><h1>Ask your restaurant data<span>.</span></h1>
          <p>Answers come from your saved records. Forecasts are clearly labeled; missing data is never filled in.</p></div>
        <button className="secondary-button" onClick={clearHistory} disabled={!messages.length || busy}>Clear history</button>
      </header>
      <div className="admin-chat-window" aria-label="Admin assistant conversation" aria-live="polite">
        {messages.length === 0 ? (
          <div className="admin-chat-welcome">
            <div className="admin-chat-orb">✦</div><h2>What would you like to know?</h2>
            <p>Ask in plain English about sales, profit, orders, stock, customers, expenses, or forecasts.</p>
            <div className="admin-chat-suggestions">{suggestedQuestions.map((suggestion) =>
              <button key={suggestion} disabled={busy} onClick={() => sendMessage(suggestion)}>{suggestion}<span>↗</span></button>
            )}</div>
          </div>
        ) : (
          <div className="admin-chat-messages">
            {messages.map((message, index) => (
              <article className={`admin-chat-message ${message.role}`} key={`${message.timestamp}-${index}`}>
                <div className="admin-chat-avatar">{message.role === "assistant" ? "✦" : (user.display_name || "A").slice(0, 1)}</div>
                <div className="admin-chat-message-content">
                  <div className="admin-chat-message-meta"><strong>{message.role === "assistant" ? "Restaurant assistant" : "You"}</strong><time>{formatTime(message.timestamp)}</time></div>
                  <div className="admin-chat-bubble">{message.role === "assistant" ? renderAnswer(message.content) : <p>{message.content}</p>}</div>
                  {message.tools?.length > 0 && <div className="admin-chat-tool-note">Checked records: {message.tools.map((tool) => tool.replaceAll("_", " ")).join(" · ")}</div>}
                </div>
              </article>
            ))}
            {busy && <article className="admin-chat-message assistant"><div className="admin-chat-avatar">✦</div><div className="admin-chat-message-content"><div className="admin-chat-message-meta"><strong>Restaurant assistant</strong><span>Checking records…</span></div><div className="admin-chat-bubble admin-chat-loading"><i /><i /><i /></div></div></article>}
            <div ref={endRef} />
          </div>
        )}
      </div>
      {error && <div className="admin-chat-error" role="alert">{error}</div>}
      <form className="admin-chat-composer" onSubmit={(event) => { event.preventDefault(); sendMessage(); }}>
        <label className="admin-chat-input-wrap"><span className="sr-only">Ask a question about restaurant business data</span>
          <textarea value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); sendMessage(); }
          }} maxLength={1000} placeholder="Ask a question about your restaurant…" rows={1} disabled={busy} />
        </label>
        {busy ? (
          <button className="admin-chat-stop" type="button" onClick={stopRequest}>Stop</button>
        ) : (
          <button className="admin-chat-send" type="submit" disabled={!question.trim()} aria-label="Send message"><span>↑</span></button>
        )}
        <small>Enter to send · Shift + Enter for a new line · Admin-only data</small>
      </form>
    </section>
  );
}
