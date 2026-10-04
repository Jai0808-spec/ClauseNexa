import React, { useState } from 'react';
import { Send, User, Bot } from 'lucide-react';
import './AskContract.css';

export default function AskContract() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([
    { id: 1, sender: 'bot', text: 'Hello. I have analyzed "apartment_lease_agreement.pdf". What would you like to know about this contract?' }
  ]);

  const handleSend = (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    // Add user message to chat
    const newMessages = [...messages, { id: Date.now(), sender: 'user', text: input }];
    setMessages(newMessages);
    setInput('');

    // Simulate AI response delay
    setTimeout(() => {
      setMessages(prev => [...prev, { 
        id: Date.now() + 1, 
        sender: 'bot', 
        text: 'Based on the context retrieved from the document, the tenant is responsible for structural repairs exceeding $500 as per Section 4.2.' 
      }]);
    }, 1000);
  };

  return (
    <div className="chat-page">
      <div className="chat-header">
        <h1>Ask Contract</h1>
        <p>Query the document using the ClauseNexa RAG pipeline.</p>
      </div>

      <div className="chat-container">
        <div className="message-list">
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
            placeholder="Ask a question about the lease..."
            className="chat-input"
          />
          <button type="submit" className="send-button" disabled={!input.trim()}>
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
}