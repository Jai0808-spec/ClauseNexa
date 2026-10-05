import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, FileText } from 'lucide-react';
import { uploadContract, listContracts, getContract, deleteContract } from '../api';
import { useSelectedContract } from '../ContractContext';
import './UploadContract.css';

export default function UploadContract() {
  const fileInputRef = useRef(null);
  const navigate = useNavigate();
  const { selectedContract, setSelectedContract } = useSelectedContract();

  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [contracts, setContracts] = useState([]);
  const [loadingList, setLoadingList] = useState(true);

  const loadContracts = async () => {
    setLoadingList(true);
    try {
      setContracts(await listContracts());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingList(false);
    }
  };

  useEffect(() => {
    loadContracts();
  }, []);

  const handleDropzoneClick = () => {
    fileInputRef.current.click();
  };

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file) {
      setSelectedFile(file);
      setError('');
    }
  };

  const handleUpload = async () => {
    setUploading(true);
    setError('');
    try {
      const result = await uploadContract(selectedFile);
      const contract = await getContract(result.contract_id);
      setSelectedContract(contract);
      setSelectedFile(null);
      await loadContracts();
      navigate('/overview');
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleOpen = (contract) => {
    setSelectedContract(contract);
    navigate('/overview');
  };

  const handleDelete = async (contract) => {
    if (!window.confirm(`Delete "${contract.file_name}"?`)) return;
    setError('');
    try {
      await deleteContract(contract.id);
      if (selectedContract?.id === contract.id) {
        setSelectedContract(null);
      }
      await loadContracts();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="upload-page">
      <div className="upload-header">
        <h1>Upload Contract</h1>
        <p>Select a PDF or Word document to begin the AI analysis pipeline.</p>
      </div>

      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept=".pdf,.docx"
        style={{ display: 'none' }}
      />

      {!selectedFile ? (
        <div className="dropzone" onClick={handleDropzoneClick}>
          <UploadCloud size={64} className="upload-icon" />
          <h3>Click to browse your files</h3>
          <p className="divider">or</p>
          <button className="browse-button" onClick={(e) => { e.stopPropagation(); handleDropzoneClick(); }}>
            Browse Files
          </button>
          <p className="file-limits">Supported formats: .pdf, .docx</p>
        </div>
      ) : (
        <div className="dropzone dropzone-ready">
          <FileText size={64} className="ready-icon" />
          <h3 className="ready-name">{selectedFile.name}</h3>
          <p className="ready-text">Ready to upload.</p>
          <div className="button-row">
            <button className="browse-button" onClick={handleUpload} disabled={uploading}>
              {uploading ? 'Uploading...' : 'Upload to ClauseNexa'}
            </button>
            <button
              className="browse-button button-danger"
              onClick={() => setSelectedFile(null)}
              disabled={uploading}
            >
              Remove File
            </button>
          </div>
        </div>
      )}

      {error && <p className="upload-error">{error}</p>}

      <section className="contract-list">
        <h2>Uploaded Contracts</h2>
        {loadingList ? (
          <p className="file-limits">Loading...</p>
        ) : contracts.length === 0 ? (
          <p className="file-limits">No contracts uploaded yet.</p>
        ) : (
          <ul>
            {contracts.map((contract) => (
              <li key={contract.id} className="contract-row">
                <div>
                  <strong>{contract.file_name}</strong>
                  <span className="contract-meta">
                    {' '}· {contract.status} · {new Date(contract.uploaded_at).toLocaleString()}
                  </span>
                </div>
                <div className="button-row">
                  <button className="row-button" onClick={() => handleOpen(contract)}>Open</button>
                  <button className="row-button button-danger" onClick={() => handleDelete(contract)}>Delete</button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
