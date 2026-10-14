import React from 'react';
import { Link } from 'react-router-dom';
import { useContractAnalysis, useSelectedContract } from '../ContractContext';
import './ContractOverview.css';

const riskClass = (level) => {
  if (level === 'High') return 'risk-high';
  if (level === 'Medium') return 'risk-medium';
  return '';
};

export default function ContractOverview() {
  const { selectedContract } = useSelectedContract();
  const { analysis, loading, error } = useContractAnalysis(selectedContract?.id);
  const summary = analysis?.summary;

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

      {loading && <p className="file-limits">Analysing contract…</p>}
      {error && <p className="file-limits">{error}</p>}

      {summary && (
        <div className="metrics-grid">
          <div className={`metric-card ${riskClass(summary.overall_risk_level)}`}>
            <h3>Overall Risk</h3>
            <p className="metric-value">{summary.overall_risk_level ?? 'None found'}</p>
          </div>
          <div className="metric-card">
            <h3>Clauses</h3>
            <p className="metric-value">{summary.total_clauses}</p>
          </div>
          <div className="metric-card risk-high">
            <h3>High Risk</h3>
            <p className="metric-value">{summary.risk_level_counts.High}</p>
          </div>
          <div className="metric-card risk-medium">
            <h3>Medium Risk</h3>
            <p className="metric-value">{summary.risk_level_counts.Medium}</p>
          </div>
          <div className="metric-card">
            <h3>Needs Review</h3>
            <p className="metric-value">{summary.needs_review_clauses}</p>
          </div>
          <div className="metric-card">
            <h3>Categories Not Found</h3>
            <p className="file-limits">
              {summary.categories_not_found.length
                ? summary.categories_not_found.join(', ')
                : 'All six categories present'}
            </p>
          </div>
        </div>
      )}

      {analysis && <p className="file-limits">{analysis.disclaimer}</p>}
    </div>
  );
}
