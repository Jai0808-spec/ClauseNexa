import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import './App.css';
import UploadContract from './pages/UploadContract';
import ContractOverview from './pages/ContractOverview';
import ClauseAnalysis from './pages/ClauseAnalysis';
import AskContract from './pages/AskContract';


export default function App() {
  return (
    <Router>
      <div className="app-container">
        <nav className="top-nav">
          <h2>ClauseNexa</h2>
          <ul>
            <li><Link to="/">Upload</Link></li>
            <li><Link to="/overview">Overview</Link></li>
            <li><Link to="/analysis">Clause Analysis</Link></li>
            <li><Link to="/ask">Ask Contract</Link></li>
          </ul>
        </nav>

        <main className="content">
          <Routes>
            {/* Replace the placeholder with your new component */}
            <Route path="/" element={<UploadContract />} />
            <Route path="/overview" element={<ContractOverview />} />
            <Route path="/analysis" element={<ClauseAnalysis />} />
            <Route path="/ask" element={<AskContract />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}
