import React, { useRef, useState } from 'react';
import { UploadCloud, FileText } from 'lucide-react';
import './UploadContract.css';

export default function UploadContract() {
  // These hooks manage the file selection logic
  const fileInputRef = useRef(null);
  const [selectedFile, setSelectedFile] = useState(null);

  // Triggers the hidden HTML file input when our custom dropzone is clicked
  const handleDropzoneClick = () => {
    fileInputRef.current.click();
  };

  // Captures the file once the user selects it from their computer
  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file) {
      setSelectedFile(file.name);
    }
  };

  return (
    <div className="upload-page">
      <div className="upload-header">
        <h1>Upload Contract</h1>
        <p>Select a PDF or Word document to begin the AI analysis pipeline.</p>
      </div>

      {/* The actual HTML file input is hidden from view */}
      <input 
        type="file" 
        ref={fileInputRef} 
        onChange={handleFileChange} 
        accept=".pdf,.docx" 
        style={{ display: 'none' }} 
      />

      {/* If no file is selected, show the upload prompt */}
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
        /* If a file is selected, show a success state */
        <div className="dropzone" style={{ borderColor: '#10b981', backgroundColor: '#ecfdf5' }}>
          <FileText size={64} style={{ color: '#10b981', marginBottom: '1rem' }} />
          <h3 style={{ color: '#065f46' }}>{selectedFile}</h3>
          <p style={{ color: '#047857', marginBottom: '1.5rem' }}>File ready for backend submission.</p>
          <button 
            className="browse-button" 
            style={{ backgroundColor: '#ef4444' }}
            onClick={() => setSelectedFile(null)}
          >
            Remove File
          </button>
        </div>
      )}
    </div>
  );
}