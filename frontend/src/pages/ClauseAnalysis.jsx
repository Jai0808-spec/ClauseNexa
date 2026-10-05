import React from 'react';
import { Link } from 'react-router-dom';
import { useSelectedContract } from '../ContractContext';
import './ClauseAnalysis.css';

export default function ClauseAnalysis() {
  const { selectedContract } = useSelectedContract();

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

      <p className="file-limits">
        Clause detection is not connected to the backend yet, so there are no clauses to show.
      </p>
    </div>
  );
}
