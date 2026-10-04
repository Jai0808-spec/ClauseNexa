export const mockContractState = {
  documentName: "apartment_lease_agreement.pdf",
  overview: {
    type: "Residential Lease",
    totalClauses: 14,
    highRisk: 2,
    mediumRisk: 1
  },
  clauses: [
    { 
      id: 1, 
      category: "Termination", 
      text: "The landlord may terminate this lease with 14 days notice if rent is unpaid.", 
      riskLevel: "High",
      reason: "Short notice period for residential eviction."
    },
    { 
      id: 2, 
      category: "Liability", 
      text: "Tenant is responsible for all structural repairs exceeding $500.", 
      riskLevel: "High",
      reason: "Shifts undue financial burden to the lessee."
    },
    {
      id: 3,
      category: "Confidentiality",
      text: "Terms of this lease shall remain confidential between parties.",
      riskLevel: "No",
      reason: "Standard clause."
    }
  ]
};
