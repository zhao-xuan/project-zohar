import React from 'react';
import { Check, Clock, AlertCircle } from 'lucide-react';
import { useWizard } from '../context/WizardContext';

export function ProgressSidebar() {
  const { state, wizardSteps } = useWizard();
  const { fileProcessingStatus } = state;

  const getStepIcon = (stepIndex: number) => {
    if (stepIndex < state.currentStep) {
      return <Check className="w-4 h-4 text-green-600" />;
    } else if (stepIndex === state.currentStep) {
      return <Clock className="w-4 h-4 text-blue-600" />;
    } else {
      return <div className="w-4 h-4 rounded-full border-2 border-gray-300" />;
    }
  };

  const getStepStatus = (stepIndex: number) => {
    if (stepIndex < state.currentStep) {
      return 'completed';
    } else if (stepIndex === state.currentStep) {
      return 'current';
    } else {
      return 'pending';
    }
  };

  return (
    <div className="progress-sidebar">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Setup Progress</h3>
      
      {/* Wizard Steps */}
      <div className="space-y-3 mb-6">
        {wizardSteps.map((step, index) => {
          const status = getStepStatus(index);
          return (
            <div
              key={step.id}
              className={`flex items-center space-x-3 p-2 rounded-md transition-colors ${
                status === 'current'
                  ? 'bg-blue-50 border border-blue-200'
                  : status === 'completed'
                  ? 'bg-green-50'
                  : 'bg-gray-50'
              }`}
            >
              {getStepIcon(index)}
              <div className="flex-1 min-w-0">
                <p
                  className={`text-sm font-medium ${
                    status === 'current'
                      ? 'text-blue-900'
                      : status === 'completed'
                      ? 'text-green-900'
                      : 'text-gray-500'
                  }`}
                >
                  {step.title}
                </p>
                <p
                  className={`text-xs ${
                    status === 'current'
                      ? 'text-blue-700'
                      : status === 'completed'
                      ? 'text-green-700'
                      : 'text-gray-400'
                  }`}
                >
                  {step.description}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* File Processing Status */}
      {(fileProcessingStatus.isProcessing || fileProcessingStatus.vectorDatabases.length > 0) && (
        <div className="border-t border-gray-200 pt-4">
          <h4 className="text-sm font-semibold text-gray-900 mb-3">File Processing</h4>
          
          {fileProcessingStatus.isProcessing && (
            <div className="space-y-2 mb-4">
              <div className="flex justify-between text-xs text-gray-600">
                <span>Progress</span>
                <span>{Math.round(fileProcessingStatus.progress)}%</span>
              </div>
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${fileProcessingStatus.progress}%` }}
                />
              </div>
              {fileProcessingStatus.currentFile && (
                <p className="text-xs text-gray-500 truncate">
                  Processing: {fileProcessingStatus.currentFile}
                </p>
              )}
              <div className="flex justify-between text-xs text-gray-600">
                <span>Files: {fileProcessingStatus.processedFiles}/{fileProcessingStatus.totalFiles}</span>
              </div>
            </div>
          )}

          {/* Errors */}
          {fileProcessingStatus.errors.length > 0 && (
            <div className="space-y-2 mb-4">
              <div className="flex items-center space-x-1">
                <AlertCircle className="w-4 h-4 text-red-500" />
                <span className="text-sm font-medium text-red-700">Errors</span>
              </div>
              <div className="space-y-1 max-h-24 overflow-y-auto">
                {fileProcessingStatus.errors.map((error, index) => (
                  <p key={index} className="text-xs text-red-600 bg-red-50 p-2 rounded">
                    {error}
                  </p>
                ))}
              </div>
            </div>
          )}

          {/* Vector Databases */}
          {fileProcessingStatus.vectorDatabases.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center space-x-1">
                <Check className="w-4 h-4 text-green-500" />
                <span className="text-sm font-medium text-green-700">Databases Created</span>
              </div>
              <div className="space-y-1">
                {fileProcessingStatus.vectorDatabases.map((db) => (
                  <div key={db.id} className="text-xs bg-green-50 p-2 rounded">
                    <p className="font-medium text-green-900">{db.name}</p>
                    <p className="text-green-700">{db.documents} documents</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
} 