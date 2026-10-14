import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { getContractAnalysis } from './api';

const ContractContext = createContext(null);

export function ContractProvider({ children }) {
  const [selectedContract, setSelectedContract] = useState(null);

  return (
    <ContractContext.Provider value={{ selectedContract, setSelectedContract }}>
      {children}
    </ContractContext.Provider>
  );
}

export function useSelectedContract() {
  return useContext(ContractContext);
}

// Analysis is expensive (Legal-BERT over every clause), so results are
// cached per contract and shared by the Overview and Clause Analysis pages.
const analysisCache = new Map();

export function useContractAnalysis(contractId) {
  const [state, setState] = useState({ analysis: null, loading: false, error: '' });
  const latestId = useRef(contractId);
  latestId.current = contractId;

  useEffect(() => {
    if (!contractId) return;

    if (analysisCache.has(contractId)) {
      setState({ analysis: analysisCache.get(contractId), loading: false, error: '' });
      return;
    }

    setState({ analysis: null, loading: true, error: '' });
    getContractAnalysis(contractId)
      .then((analysis) => {
        analysisCache.set(contractId, analysis);
        if (latestId.current === contractId) setState({ analysis, loading: false, error: '' });
      })
      .catch((err) => {
        if (latestId.current === contractId) {
          setState({ analysis: null, loading: false, error: err.message });
        }
      });
  }, [contractId]);

  return state;
}
