import React, { useState } from 'react';
import { Send, User, Bot } from 'lucide-react';
import { askContract } from '../api';
import { useSelectedContract } from '../ContractContext';
import './AskContract.css';

export default function AskContract() {
  const { selectedContract } = useSelectedContract();
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [sending, setSending] = useState(false);

  const documentName = selectedContract?.file_name;

  const greeting = documentName
    ? `Hello. You are asking about "${documentName}".`
    : 'Hello. Select a contract on the Upload page first.';

  const handleSend = async (e) => {
    e.preventDefault();
    const question = input.trim();
    if (!question || !selectedContract || sending) return;

    const id = Date.now();
    setMessages((prev) => [...prev, { id, sender: 'user', text: question }]);
    setInput('');
    setSending(true);

    try {
      const result = await askContract(selectedContract.id, question);
      setMessages((prev) => [
        ...prev,
        { id: id + 1, sender: 'bot', text: result.answer, sources: result.sources },
      ]);
    } catch (err) {
      setMessages((prev) => [...prev, { id: id + 1, sender: 'bot', text: err.message }]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="chat-page">
      <div className="chat-header">
        <h1>Ask Contract</h1>
        <p>Query the document using the ClauseNexa RAG pipeline.</p>
      </div>

      <div className="chat-container">
        <div className="message-list">
          <div className="message-wrapper bot">
            <div className="avatar">
              <Bot size={20} />
            </div>
            <div className="message-bubble">
              <p>{greeting}</p>
            </div>
          </div>

          {messages.map((msg) => (
            <div key={msg.id} className={`message-wrapper ${msg.sender}`}>
              <div className="avatar">
                {msg.sender === 'bot' ? <Bot size={20} /> : <User size={20} />}
              </div>
              <div className="message-bubble">
                <p>{msg.text}</p>
                {msg.sources?.length > 0 && (
                  <div className="sources">
                    <span className="sources-label">Sources:</span>
                    {msg.sources.map((src) => (
                      <details key={src.chunk_index} className="source-item">
                        <summary>
                          Chunk {src.chunk_index}
                          {src.page_number ? ` · p. ${src.page_number}` : ''}
                          {src.similarity != null ? ` · ${Math.round(src.similarity * 100)}% match` : ''}
                        </summary>
                        <p className="source-text">{src.text}</p>
                      </details>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          {sending && (
            <div className="message-wrapper bot">
              <div className="avatar">
                <Bot size={20} />
              </div>
              <div className="message-bubble">
                <p>Thinking…</p>
              </div>
            </div>
          )}
        </div>

        <form className="chat-input-area" onSubmit={handleSend}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about the contract..."
            className="chat-input"
            disabled={!selectedContract}
          />
          <button type="submit" className="send-button" disabled={!input.trim() || !selectedContract || sending}>
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
}
