import React from 'react';
import { Link } from 'react-router-dom';
import { useContractAnalysis, useSelectedContract } from '../ContractContext';
import './ClauseAnalysis.css';

const riskClass = (level) => {
  if (level === 'High') return 'risk-high';
  if (level === 'Medium') return 'risk-medium';
  return '';
};

export default function ClauseAnalysis() {
  const { selectedContract } = useSelectedContract();
  const { analysis, loading, error } = useContractAnalysis(selectedContract?.id);

  if (!selectedContract) {
    return (
      <p>
        No contract selected. <Link to="/">Upload or choose a contract</Link> first.
      </p>
    );
  }

  return (
    <div className="analysis-page">
      <div className="analysis-header">
        <h1>Clause Breakdown</h1>
        <p>Detailed risk assessment for {selectedContract.file_name}</p>
      </div>

      {loading && <p className="file-limits">Analysing clauses…</p>}
      {error && <p className="file-limits">{error}</p>}

      {analysis && (
        <div className="clause-grid">
          {analysis.clauses.map((clause) => (
            <div
              key={clause.clause_number}
              className={`clause-card ${riskClass(clause.risk_level)}`}
            >
              <div className="clause-card-header">
                <span className="clause-category">{clause.predicted_category}</span>
                <span className={`risk-badge ${riskClass(clause.risk_level)}`}>
                  {clause.risk_level}
                </span>
              </div>
              <div className="clause-content">
                <h4>Clause text</h4>
                <p className="extracted-text">{clause.clause_text}</p>
              </div>
              <div className="clause-reasoning">
                <h4>Reasoning</h4>
                {clause.risk_reasons.map((reason) => (
                  <p key={reason}>{reason}</p>
                ))}
              </div>
            </div>
          ))}
          <p className="file-limits">{analysis.disclaimer}</p>
        </div>
      )}
    </div>
  );
}
