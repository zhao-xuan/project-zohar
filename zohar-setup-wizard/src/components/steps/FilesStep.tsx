import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { ArrowLeft, ArrowRight, Upload, Folder, File, Play, Pause, X } from 'lucide-react';
import { useWizard } from '../../context/WizardContext';
import { WizardLayout } from '../WizardLayout';

export function FilesStep() {
  const { state, dispatch, nextStep, previousStep } = useWizard();
  const { fileProcessingStatus } = state;
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [selectedFolders, setSelectedFolders] = useState<string[]>([]);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setSelectedFiles(prev => [...prev, ...acceptedFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: true,
    accept: {
      'text/*': ['.txt', '.md', '.csv'],
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.ms-excel': ['.xls'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/json': ['.json'],
      'image/*': ['.png', '.jpg', '.jpeg', '.gif', '.bmp'],
      'audio/*': ['.mp3', '.wav', '.m4a', '.ogg'],
      'video/*': ['.mp4', '.avi', '.mov', '.wmv']
    }
  });

  const handleFolderSelect = () => {
    // In a real Tauri app, this would use the Tauri file system API
    // For now, we'll simulate folder selection
    const folderPath = prompt('Enter folder path (e.g., /Users/user/Documents):');
    if (folderPath) {
      setSelectedFolders(prev => [...prev, folderPath]);
    }
  };

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const removeFolder = (index: number) => {
    setSelectedFolders(prev => prev.filter((_, i) => i !== index));
  };

  const startProcessing = async () => {
    const totalItems = selectedFiles.length + selectedFolders.length;
    
    dispatch({
      type: 'UPDATE_FILE_PROCESSING',
      payload: {
        isProcessing: true,
        progress: 0,
        totalFiles: totalItems,
        processedFiles: 0,
        currentFile: undefined,
        errors: []
      }
    });

    // Simulate file processing
    for (let i = 0; i < totalItems; i++) {
      const isFile = i < selectedFiles.length;
      const item = isFile ? selectedFiles[i].name : selectedFolders[i - selectedFiles.length];
      
      dispatch({
        type: 'UPDATE_FILE_PROCESSING',
        payload: {
          currentFile: item,
          progress: (i / totalItems) * 100,
          processedFiles: i
        }
      });

      // Simulate processing time
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Simulate random errors (10% chance)
      if (Math.random() < 0.1) {
        dispatch({
          type: 'UPDATE_FILE_PROCESSING',
          payload: {
            errors: [...fileProcessingStatus.errors, `Failed to process: ${item}`]
          }
        });
      }
    }

    // Complete processing and generate mock vector databases
    const mockDatabases: typeof fileProcessingStatus.vectorDatabases = [
      {
        id: 'personal_documents',
        name: 'Personal Documents',
        documents: Math.floor(Math.random() * 500) + 100,
        structure: {
          content: { type: 'text', description: 'Main document content' },
          filename: { type: 'string', description: 'Original filename' },
          file_type: { type: 'string', description: 'MIME type' },
          created_at: { type: 'datetime', description: 'Processing timestamp' },
          chunk_id: { type: 'integer', description: 'Chunk identifier' }
        },
        path: '/data/vector_db/personal_documents'
      },
      {
        id: 'media_content',
        name: 'Media Content',
        documents: Math.floor(Math.random() * 200) + 50,
        structure: {
          description: { type: 'text', description: 'AI-generated description' },
          file_path: { type: 'string', description: 'File location' },
          media_type: { type: 'string', description: 'Image/audio/video' },
          metadata: { type: 'json', description: 'Technical metadata' }
        },
        path: '/data/vector_db/media_content'
      }
    ];

    dispatch({
      type: 'UPDATE_FILE_PROCESSING',
      payload: {
        isProcessing: false,
        progress: 100,
        processedFiles: totalItems,
        currentFile: undefined,
        vectorDatabases: mockDatabases
      }
    });
  };

  const canStartProcessing = selectedFiles.length > 0 || selectedFolders.length > 0;
  const hasProcessedData = fileProcessingStatus.vectorDatabases.length > 0;

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <WizardLayout 
      title="Process Files"
      subtitle="Upload files or select folders to create your intelligent knowledge base"
    >
      <div className="space-y-6">
        {/* File Drop Zone */}
        {!fileProcessingStatus.isProcessing && (
          <div
            {...getRootProps()}
            className={`dropzone ${isDragActive ? 'active' : ''}`}
          >
            <input {...getInputProps()} />
            <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            {isDragActive ? (
              <p className="text-lg text-primary-600 font-medium">Drop files here...</p>
            ) : (
              <div className="text-center">
                <p className="text-lg text-gray-600 font-medium mb-2">
                  Drag & drop files here, or click to select
                </p>
                <p className="text-sm text-gray-500">
                  Supports: PDF, Word, Excel, Images, Audio, Video, Text files
                </p>
              </div>
            )}
          </div>
        )}

        {/* Folder Selection */}
        {!fileProcessingStatus.isProcessing && (
          <div className="text-center">
            <button
              onClick={handleFolderSelect}
              className="btn-secondary flex items-center space-x-2 mx-auto"
            >
              <Folder className="w-5 h-5" />
              <span>Select Folder</span>
            </button>
            <p className="text-sm text-gray-500 mt-2">
              Select entire folders to process all files within them
            </p>
          </div>
        )}

        {/* Selected Files */}
        {selectedFiles.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-lg font-semibold text-gray-900">Selected Files ({selectedFiles.length})</h3>
            <div className="max-h-48 overflow-y-auto space-y-2">
              {selectedFiles.map((file, index) => (
                <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center space-x-3">
                    <File className="w-5 h-5 text-gray-500" />
                    <div>
                      <p className="text-sm font-medium text-gray-900">{file.name}</p>
                      <p className="text-xs text-gray-500">{formatFileSize(file.size)}</p>
                    </div>
                  </div>
                  {!fileProcessingStatus.isProcessing && (
                    <button
                      onClick={() => removeFile(index)}
                      className="text-red-500 hover:text-red-700"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Selected Folders */}
        {selectedFolders.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-lg font-semibold text-gray-900">Selected Folders ({selectedFolders.length})</h3>
            <div className="space-y-2">
              {selectedFolders.map((folder, index) => (
                <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center space-x-3">
                    <Folder className="w-5 h-5 text-gray-500" />
                    <p className="text-sm font-medium text-gray-900">{folder}</p>
                  </div>
                  {!fileProcessingStatus.isProcessing && (
                    <button
                      onClick={() => removeFolder(index)}
                      className="text-red-500 hover:text-red-700"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Processing Controls */}
        {canStartProcessing && !fileProcessingStatus.isProcessing && !hasProcessedData && (
          <div className="text-center">
            <button
              onClick={startProcessing}
              className="btn-primary flex items-center space-x-2 mx-auto"
            >
              <Play className="w-5 h-5" />
              <span>Start Processing</span>
            </button>
            <p className="text-sm text-gray-600 mt-2">
              This will analyze your files and create searchable vector databases
            </p>
          </div>
        )}

        {/* Processing Status */}
        {fileProcessingStatus.isProcessing && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-blue-900">Processing Files...</h3>
              <Pause className="w-5 h-5 text-blue-600" />
            </div>
            
            <div className="space-y-3">
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${fileProcessingStatus.progress}%` }}
                />
              </div>
              
              <div className="flex justify-between text-sm text-blue-700">
                <span>Progress: {Math.round(fileProcessingStatus.progress)}%</span>
                <span>{fileProcessingStatus.processedFiles} / {fileProcessingStatus.totalFiles} files</span>
              </div>
              
              {fileProcessingStatus.currentFile && (
                <p className="text-sm text-blue-600">
                  Currently processing: {fileProcessingStatus.currentFile}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Processing Complete */}
        {hasProcessedData && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-green-900 mb-4">Processing Complete!</h3>
            <p className="text-green-700 mb-4">
              Successfully processed {fileProcessingStatus.processedFiles} files and created {fileProcessingStatus.vectorDatabases.length} vector databases.
            </p>
            
            <div className="space-y-2">
              {fileProcessingStatus.vectorDatabases.map(db => (
                <div key={db.id} className="flex items-center justify-between p-3 bg-white rounded border">
                  <div>
                    <p className="font-medium text-gray-900">{db.name}</p>
                    <p className="text-sm text-gray-600">{db.documents} documents indexed</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Processing Errors */}
        {fileProcessingStatus.errors.length > 0 && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <h4 className="text-lg font-semibold text-red-900 mb-2">Processing Errors</h4>
            <div className="space-y-1">
              {fileProcessingStatus.errors.map((error, index) => (
                <p key={index} className="text-sm text-red-700">{error}</p>
              ))}
            </div>
          </div>
        )}

        {/* Navigation */}
        <div className="wizard-navigation">
          <button
            onClick={previousStep}
            className="btn-secondary flex items-center space-x-2"
          >
            <ArrowLeft className="w-5 h-5" />
            <span>Back</span>
          </button>
          
          <button
            onClick={nextStep}
            disabled={!hasProcessedData}
            className="btn-primary flex items-center space-x-2"
          >
            <span>Continue</span>
            <ArrowRight className="w-5 h-5" />
          </button>
        </div>
      </div>
    </WizardLayout>
  );
} 