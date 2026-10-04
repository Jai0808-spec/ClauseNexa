import React from 'react';
import { mockContractState } from '../mockData';
import './ClauseAnalysis.css';

export default function ClauseAnalysis() {
  const { clauses, documentName } = mockContractState;

  return (
    <div className="analysis-page">
      <div className="analysis-header">
        <h1>Clause Breakdown</h1>
        <p>Detailed risk assessment for {documentName}</p>
      </div>

      <div className="clause-grid">
        {clauses.map((clause) => (
          <div key={clause.id} className={`clause-card risk-${clause.riskLevel.toLowerCase()}`}>
            <div className="clause-card-header">
              <span className="clause-category">{clause.category}</span>
              <span className={`risk-badge risk-${clause.riskLevel.toLowerCase()}`}>
                {clause.riskLevel} Risk
              </span>
            </div>
            
            <div className="clause-content">
              <h4>Extracted Text:</h4>
              <p className="extracted-text">"{clause.text}"</p>
            </div>

            <div className="clause-reasoning">
              <h4>AI Reasoning:</h4>
              <p>{clause.reason}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}