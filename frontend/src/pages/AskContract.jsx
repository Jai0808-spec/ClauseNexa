import React, { useState } from 'react';
import { Send, User, Bot } from 'lucide-react';
import { useSelectedContract } from '../ContractContext';
import './AskContract.css';

export default function AskContract() {
  const { selectedContract } = useSelectedContract();
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);

  const documentName = selectedContract?.file_name;

  const greeting = documentName
    ? `Hello. You are asking about "${documentName}".`
    : 'Hello. Select a contract on the Upload page first.';

  const handleSend = (e) => {
    e.preventDefault();
    if (!input.trim() || !selectedContract) return;

    setMessages((prev) => [
      ...prev,
      { id: Date.now(), sender: 'user', text: input },
      {
        id: Date.now() + 1,
        sender: 'bot',
        text: 'Question answering is not connected to the backend yet.',
      },
    ]);
    setInput('');
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
              </div>
            </div>
          ))}
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
          <button type="submit" className="send-button" disabled={!input.trim() || !selectedContract}>
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
}
