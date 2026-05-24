import React, { useState, useRef, useEffect } from 'react';
import './UploadCV.css';

interface UploadCVProps {
  onCandidateAdded: () => void;
}

interface ExtractedData {
  name: string;
  seniority: string;
  years_of_experience: string;
  current_role: string;
  previous_jobs: string;
  degrees: string;
  location: string;
  languages: string;
  technologies: string;
  project_summary: string;
  linkedin_url: string;
  email: string;
  [key: string]: string;
}

const UploadCV: React.FC<UploadCVProps> = ({ onCandidateAdded }) => {
  const [file, setFile] = useState<File | null>(null);
  const [pastedText, setPastedText] = useState('');
  const [extractedData, setExtractedData] = useState<ExtractedData | null>(null);
  const [isDuplicate, setIsDuplicate] = useState(false);
  const [existingRecord, setExistingRecord] = useState<any>(null);
  const [isExtracting, setIsExtracting] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [message, setMessage] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);

  // Clean up object URL when component unmounts or PDF changes
  useEffect(() => {
    return () => {
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    };
  }, [pdfUrl]);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') setDragActive(true);
    else if (e.type === 'dragleave') setDragActive(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files?.[0]) {
      const droppedFile = e.dataTransfer.files[0];
      setFile(droppedFile);
      setExtractedData(null);
      setSuccessMsg('');
      // Create preview URL for PDF
      if (droppedFile.type === 'application/pdf') {
        if (pdfUrl) URL.revokeObjectURL(pdfUrl);
        setPdfUrl(URL.createObjectURL(droppedFile));
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      const selectedFile = e.target.files[0];
      setFile(selectedFile);
      setExtractedData(null);
      setSuccessMsg('');
      // Create preview URL for PDF
      if (selectedFile.type === 'application/pdf') {
        if (pdfUrl) URL.revokeObjectURL(pdfUrl);
        setPdfUrl(URL.createObjectURL(selectedFile));
      }
    }
  };

  const handleExtract = async () => {
    setIsExtracting(true);
    setMessage('');
    setSuccessMsg('');

    try {
      const formData = new FormData();
      if (file) {
        formData.append('file', file);
      } else if (pastedText.trim()) {
        formData.append('text', pastedText);
      } else {
        setMessage('Please upload a PDF or paste LinkedIn text.');
        setIsExtracting(false);
        return;
      }

      const res = await fetch('http://127.0.0.1:8000/api/ingest', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      const data = await res.json();

      setExtractedData(data.extracted_data);
      setIsDuplicate(data.is_duplicate);
      setExistingRecord(data.existing_record);
      setMessage(data.message);
    } catch (err) {
      setMessage(`Extraction failed: ${err}`);
    } finally {
      setIsExtracting(false);
    }
  };

  const handleFieldChange = (field: string, value: string) => {
    if (extractedData) {
      setExtractedData({ ...extractedData, [field]: value });
    }
  };

  const handleApprove = async () => {
    if (!extractedData) return;
    setIsApproving(true);

    try {
      const res = await fetch('http://127.0.0.1:8000/api/ingest/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ candidate_data: extractedData }),
      });

      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      const data = await res.json();

      setSuccessMsg(data.message);
      setExtractedData(null);
      setFile(null);
      setPastedText('');
      if (pdfUrl) {
        URL.revokeObjectURL(pdfUrl);
        setPdfUrl(null);
      }
      onCandidateAdded();
    } catch (err) {
      setMessage(`Approval failed: ${err}`);
    } finally {
      setIsApproving(false);
    }
  };

  const handleBack = () => {
    setExtractedData(null);
    setMessage('');
  };

  const fieldLabels: Record<string, string> = {
    name: 'Full Name', seniority: 'Seniority Level', years_of_experience: 'Years of Experience',
    current_role: 'Current Role', previous_jobs: 'Previous Jobs', degrees: 'Degrees',
    location: 'Location', languages: 'Languages Spoken', technologies: 'Technologies',
    project_summary: 'Project Summary', linkedin_url: 'LinkedIn URL', email: 'Email',
  };

  return (
    <div className="upload-cv">
      <div className="section-header">
        <div>
          <div className="section-title">Upload CV / LinkedIn Profile</div>
          <div className="section-subtitle">Module 1: AI extracts candidate data for your review</div>
        </div>
      </div>

      <div className="upload-content">
        {/* Step 1: Upload */}
        {!extractedData && (
          <div className="upload-area">
            <div className="upload-methods">
              <div
                className={`drop-zone ${dragActive ? 'active' : ''} ${file ? 'has-file' : ''}`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <input ref={fileInputRef} type="file" accept=".pdf" onChange={handleFileSelect} hidden />
                {file ? (
                  <>
                    <div className="drop-icon"></div>
                    <div className="drop-text">{file.name}</div>
                    <div className="drop-hint">Click to change file</div>
                  </>
                ) : (
                  <>
                    <div className="drop-icon"></div>
                    <div className="drop-text">Drop PDF here or click to browse</div>
                    <div className="drop-hint">Supports CV files in PDF format</div>
                  </>
                )}
              </div>

              <div className="upload-divider"><span>OR</span></div>

              <div className="paste-area">
                <textarea
                  className="form-textarea paste-input"
                  placeholder="Paste LinkedIn profile text here..."
                  value={pastedText}
                  onChange={e => setPastedText(e.target.value)}
                  rows={6}
                />
              </div>
            </div>

            <button
              className="btn btn-primary extract-btn"
              onClick={handleExtract}
              disabled={isExtracting || (!file && !pastedText.trim())}
            >
              {isExtracting ? (
                <><span className="spinner"></span> Extracting with AI...</>
              ) : (
                'Extract with AI (NER)'
              )}
            </button>
          </div>
        )}

        {/* Step 2: Review (Human-in-the-Loop) — with embedded PDF viewer */}
        {extractedData && (
          <div className={`review-area ${pdfUrl ? 'has-pdf' : ''}`}>
            <div className="review-header">
              <h3>Review Extracted Data</h3>
              <p className="review-hint">Edit any field before approving. All data is AI-extracted — please verify.</p>
            </div>

            {isDuplicate && (
              <div className="duplicate-warning">
                <strong>Duplicate candidate detected!</strong> 
                Clicking 'Approve & Merge' will intelligently blend this new data into their existing profile.
              </div>
            )}

            <div className={`review-split-layout ${pdfUrl ? 'split' : 'no-pdf'}`}>
              {/* Left: PDF Viewer */}
              {pdfUrl && (
                <div className="pdf-viewer-panel">
                  <div className="pdf-viewer-header">
                    <span className="pdf-viewer-title">Original CV</span>
                    <span className="pdf-viewer-filename">{file?.name}</span>
                  </div>
                  <iframe
                    src={pdfUrl}
                    className="pdf-iframe"
                    title="CV PDF Preview"
                  />
                </div>
              )}

              {/* Right: Editable form */}
              <div className="review-form-panel">
                <div className="review-grid">
                  {Object.entries(fieldLabels).map(([key, label]) => (
                    <div key={key} className={`form-group ${key === 'project_summary' || key === 'previous_jobs' ? 'full-width' : ''}`}>
                      <label className="form-label">{label}</label>
                      {key === 'project_summary' || key === 'previous_jobs' ? (
                        <textarea
                          className="form-textarea"
                          value={extractedData[key] || ''}
                          onChange={e => handleFieldChange(key, e.target.value)}
                          rows={3}
                        />
                      ) : (
                        <input
                          className="form-input"
                          value={extractedData[key] || ''}
                          onChange={e => handleFieldChange(key, e.target.value)}
                        />
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="review-actions">
              <button className="btn btn-secondary" onClick={handleBack}>
                ← Back
              </button>
              <button className="btn btn-success" onClick={handleApprove} disabled={isApproving}>
                {isApproving 
                  ? (isDuplicate ? 'Merging...' : 'Adding...') 
                  : (isDuplicate ? 'Approve & Merge' : 'Approve & Add to Pool')}
              </button>
            </div>
          </div>
        )}

        {message && !successMsg && <div className="info-msg">{message}</div>}
        {successMsg && <div className="success-msg">{successMsg}</div>}
      </div>
    </div>
  );
};

export default UploadCV;
