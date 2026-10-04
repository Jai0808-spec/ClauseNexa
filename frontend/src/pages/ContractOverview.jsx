import React from 'react';
import { mockContractState } from '../mockData';
import './ContractOverview.css';

export default function ContractOverview() {
  const { overview, documentName } = mockContractState;

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Analysis Report: {documentName}</h1>
        <span className="badge">{overview.type}</span>
      </header>

      <div className="metrics-grid">
        <div className="metric-card">
          <h3>Total Clauses Detected</h3>
          <p className="metric-value">{overview.totalClauses}</p>
        </div>
        <div className="metric-card risk-high">
          <h3>High Attention Required</h3>
          <p className="metric-value">{overview.highRisk}</p>
        </div>
        <div className="metric-card risk-medium">
          <h3>Medium Attention Required</h3>
          <p className="metric-value">{overview.mediumRisk}</p>
        </div>
      </div>
    </div>
  );
}