import React, { createContext, useContext, useState } from 'react';

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
