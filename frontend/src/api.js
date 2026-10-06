const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  const body = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      typeof body.detail === 'string' ? body.detail : `Request failed (${response.status})`
    );
  }

  return body;
}

export async function uploadContract(file) {
  const formData = new FormData();
  formData.append('file', file);
  return request('/contracts/upload', { method: 'POST', body: formData });
}

export async function listContracts() {
  const body = await request('/contracts');
  return body.contracts;
}

export function getContract(contractId) {
  return request(`/contracts/${contractId}`);
}

export function deleteContract(contractId) {
  return request(`/contracts/${contractId}`, { method: 'DELETE' });
}

export function processContract(contractId) {
  return request(`/contracts/${contractId}/process`, { method: 'POST' });
}
