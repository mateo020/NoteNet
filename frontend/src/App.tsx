import { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate } from 'react-router-dom';
import { Graph } from './components/Graph';
import './App.css';

function UploadForm() {
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [documentFile, setDocumentFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string>('');
  const [isUploading, setIsUploading] = useState(false);
  const [showGraph, setShowGraph] = useState(false);
  const navigate = useNavigate();

  const handleAudioChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      if (file.type.startsWith('audio/')) {
        setAudioFile(file);
        setUploadStatus('');
      } else {
        setUploadStatus('Please select a valid audio file (MP3, WAV, OGG)');
      }
    }
  };

  const handleDocumentChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      if (file.type.startsWith('image/') || file.type === 'application/pdf') {
        setDocumentFile(file);
        setUploadStatus('');
      } else {
        setUploadStatus('Please select a valid image (JPEG, PNG, GIF, WEBP) or PDF file');
      }
    }
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsUploading(true);
    setUploadStatus('');
    setShowGraph(false);

    try {
      if (audioFile) {
        const audioFormData = new FormData();
        audioFormData.append('file', audioFile);
        
        const audioResponse = await fetch('http://localhost:8000/api/upload_file', {
          method: 'POST',
          body: audioFormData,
        });

        if (!audioResponse.ok) {
          throw new Error('Audio upload failed');
        }
      }

      if (documentFile) {
        const documentFormData = new FormData();
        documentFormData.append('file', documentFile);
        
        const documentResponse = await fetch('http://localhost:8000/api/upload_file', {
          method: 'POST',
          body: documentFormData,
        });

        if (!documentResponse.ok) {
          throw new Error('Document upload failed');
        }
      }

      setUploadStatus('Files uploaded successfully! Processing...');
      // Wait a moment for the backend to process the files
      setTimeout(() => {
        setShowGraph(true);
      }, 2000);
    } catch (error) {
      setUploadStatus('Error uploading files. Please try again.');
      console.error('Upload error:', error);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="app-container">
      <h1>Welcome to NoteNet</h1>
      <p className="subtitle">Upload your audio and documents</p>
      
      <form onSubmit={handleSubmit} className="upload-form">
        <div className="upload-section">
          <h2>Audio File</h2>
          <input
            type="file"
            accept="audio/*"
            onChange={handleAudioChange}
            className="file-input"
          />
          {audioFile && (
            <p className="file-info">Selected: {audioFile.name}</p>
          )}
        </div>

        <div className="upload-section">
          <h2>Document (Image/PDF)</h2>
          <input
            type="file"
            accept="image/*,.pdf"
            onChange={handleDocumentChange}
            className="file-input"
          />
          {documentFile && (
            <p className="file-info">Selected: {documentFile.name}</p>
          )}
        </div>

        <button 
          type="submit" 
          className="submit-button"
          disabled={isUploading || (!audioFile && !documentFile)}
        >
          {isUploading ? 'Uploading...' : 'Upload Files'}
        </button>

        {uploadStatus && (
          <p className={`status-message ${uploadStatus.includes('Error') ? 'error' : 'success'}`}>
            {uploadStatus}
          </p>
        )}
      </form>

      {showGraph && (
        <div className="graph-section">
          <h2>Knowledge Graph</h2>
          <Graph />
        </div>
      )}
    </div>
  );
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<UploadForm />} />
        <Route path="/graph" element={<Graph />} />
      </Routes>
    </Router>
  );
}

export default App;