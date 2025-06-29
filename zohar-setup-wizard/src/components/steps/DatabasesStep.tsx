import React, { useState } from 'react';
import { ArrowLeft, ArrowRight, Database, ChevronDown, ChevronRight, Eye, Search } from 'lucide-react';
import { useWizard } from '../../context/WizardContext';
import { WizardLayout } from '../WizardLayout';
import { VectorDatabase } from '../../types/wizard';

export function DatabasesStep() {
  const { state, nextStep, previousStep } = useWizard();
  const { fileProcessingStatus } = state;
  const [expandedDatabases, setExpandedDatabases] = useState<Record<string, boolean>>({});
  const [searchQuery, setSearchQuery] = useState('');

  const toggleDatabaseExpansion = (databaseId: string) => {
    setExpandedDatabases(prev => ({
      ...prev,
      [databaseId]: !prev[databaseId]
    }));
  };

  const filteredDatabases = fileProcessingStatus.vectorDatabases.filter(db =>
    db.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    db.id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <WizardLayout 
      title="Vector Databases"
      subtitle="Review your generated knowledge bases and their structures"
    >
      <div className="space-y-6">
        {/* Overview */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <div className="flex items-center space-x-3 mb-4">
            <Database className="w-8 h-8 text-blue-600" />
            <div>
              <h3 className="text-lg font-semibold text-blue-900">Knowledge Base Created</h3>
              <p className="text-blue-700">
                Your files have been processed and organized into searchable vector databases
              </p>
            </div>
          </div>
          
          <div className="grid md:grid-cols-3 gap-4">
            <div className="bg-white rounded-lg p-4">
              <p className="text-2xl font-bold text-blue-600">
                {fileProcessingStatus.vectorDatabases.length}
              </p>
              <p className="text-sm text-gray-600">Databases Created</p>
            </div>
            <div className="bg-white rounded-lg p-4">
              <p className="text-2xl font-bold text-green-600">
                {fileProcessingStatus.vectorDatabases.reduce((sum, db) => sum + db.documents, 0)}
              </p>
              <p className="text-sm text-gray-600">Total Documents</p>
            </div>
            <div className="bg-white rounded-lg p-4">
              <p className="text-2xl font-bold text-purple-600">
                {fileProcessingStatus.processedFiles}
              </p>
              <p className="text-sm text-gray-600">Files Processed</p>
            </div>
          </div>
        </div>

        {/* Search */}
        {filteredDatabases.length > 1 && (
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search databases..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="form-input pl-10"
            />
          </div>
        )}

        {/* Databases List */}
        <div className="space-y-4">
          {filteredDatabases.map((database) => {
            const isExpanded = expandedDatabases[database.id];
            
            return (
              <div key={database.id} className="border border-gray-200 rounded-lg overflow-hidden">
                {/* Database Header */}
                <div 
                  className="p-6 bg-gray-50 cursor-pointer hover:bg-gray-100 transition-colors"
                  onClick={() => toggleDatabaseExpansion(database.id)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <Database className="w-6 h-6 text-primary-600" />
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900">
                          {database.name}
                        </h3>
                        <p className="text-sm text-gray-600">
                          {database.documents.toLocaleString()} documents • {database.id}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-3">
                      <div className="status-indicator status-success">
                        <span>Ready</span>
                      </div>
                      {isExpanded ? (
                        <ChevronDown className="w-5 h-5 text-gray-500" />
                      ) : (
                        <ChevronRight className="w-5 h-5 text-gray-500" />
                      )}
                    </div>
                  </div>
                </div>

                {/* Database Details */}
                {isExpanded && (
                  <div className="p-6 border-t border-gray-200 bg-white">
                    <div className="grid md:grid-cols-2 gap-6">
                      {/* Database Info */}
                      <div>
                        <h4 className="text-md font-semibold text-gray-900 mb-3">Database Information</h4>
                        <div className="space-y-2">
                          <div className="flex justify-between">
                            <span className="text-sm text-gray-600">Database ID:</span>
                            <span className="text-sm font-mono text-gray-900">{database.id}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-sm text-gray-600">Documents:</span>
                            <span className="text-sm font-medium text-gray-900">
                              {database.documents.toLocaleString()}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-sm text-gray-600">Storage Path:</span>
                            <span className="text-sm font-mono text-gray-700 truncate max-w-48">
                              {database.path}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Schema Structure */}
                      <div>
                        <h4 className="text-md font-semibold text-gray-900 mb-3">
                          Data Schema ({Object.keys(database.structure).length} fields)
                        </h4>
                        <div className="space-y-2 max-h-48 overflow-y-auto">
                          {Object.entries(database.structure).map(([field, schema]) => (
                            <div key={field} className="p-3 bg-gray-50 rounded-md">
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-sm font-medium text-gray-900">{field}</span>
                                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-primary-100 text-primary-800">
                                  {schema.type}
                                </span>
                              </div>
                              <p className="text-xs text-gray-600">{schema.description}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Sample Query Examples */}
                    <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
                      <h5 className="text-sm font-semibold text-green-900 mb-2 flex items-center">
                        <Eye className="w-4 h-4 mr-2" />
                        Sample Queries You Can Ask
                      </h5>
                      <div className="grid md:grid-cols-2 gap-2">
                        {database.id === 'personal_documents' ? [
                          '"Find documents about project planning"',
                          '"What are my recent meeting notes?"',
                          '"Show me financial documents from last year"',
                          '"Find emails mentioning budget approval"'
                        ] : [
                          '"Show me photos from vacation"',
                          '"Find audio files with speech"',
                          '"What videos do I have about cooking?"',
                          '"Show me images with text content"'
                        ].map((query, index) => (
                          <div key={index} className="text-xs text-green-700 bg-white p-2 rounded border">
                            {query}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Technical Details */}
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Technical Implementation</h3>
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <h4 className="text-md font-semibold text-gray-700 mb-2">Dynamic Schema Generation</h4>
              <p className="text-sm text-gray-600 mb-4">
                Each database was automatically structured based on your content analysis:
              </p>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• Content type detection and classification</li>
                <li>• Metadata extraction and indexing</li>
                <li>• Semantic embeddings for search</li>
                <li>• Optimized chunking strategies</li>
              </ul>
            </div>
            <div>
              <h4 className="text-md font-semibold text-gray-700 mb-2">Search Capabilities</h4>
              <p className="text-sm text-gray-600 mb-4">
                Your assistant can now perform:
              </p>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• Semantic search across all content</li>
                <li>• Multi-modal query understanding</li>
                <li>• Contextual document retrieval</li>
                <li>• Cross-reference information</li>
              </ul>
            </div>
          </div>
        </div>

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