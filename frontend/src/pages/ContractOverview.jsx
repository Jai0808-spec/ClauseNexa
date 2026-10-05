import React from 'react';
import { Link } from 'react-router-dom';
import { useSelectedContract } from '../ContractContext';
import './ContractOverview.css';

export default function ContractOverview() {
  const { selectedContract } = useSelectedContract();

  if (!selectedContract) {
    return (
      <p>
        No contract selected. <Link to="/">Upload or choose a contract</Link> first.
      </p>
    );
  }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Analysis Report: {selectedContract.file_name}</h1>
        <span className="badge">{selectedContract.file_type}</span>
      </header>

      <div className="metrics-grid">
        <div className="metric-card">
          <h3>Status</h3>
          <p className="metric-value">{selectedContract.status}</p>
        </div>
        <div className="metric-card">
          <h3>Total Pages</h3>
          <p className="metric-value">{selectedContract.total_pages ?? 'Pending'}</p>
        </div>
        <div className="metric-card">
          <h3>Uploaded</h3>
          <p className="metric-value">{new Date(selectedContract.uploaded_at).toLocaleString()}</p>
        </div>
      </div>

      <p className="file-limits">
        Clause and risk metrics will appear here once the NLP pipeline is connected to the backend.
      </p>
    </div>
  );
}
