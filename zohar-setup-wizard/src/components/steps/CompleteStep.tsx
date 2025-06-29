import React, { useEffect } from 'react';
import { CheckCircle, ExternalLink, Copy, Folder, Globe, Settings } from 'lucide-react';
import { useWizard } from '../../context/WizardContext';
import { WizardLayout } from '../WizardLayout';

export function CompleteStep() {
  const { state, dispatch } = useWizard();
  const { 
    selectedFeatures, 
    platformCredentials, 
    selectedActions, 
    fileProcessingStatus, 
    botSettings,
    vectorDatabaseLocation,
    localEndpoint
  } = state;

  useEffect(() => {
    // Simulate final setup completion
    const completeSetup = async () => {
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      dispatch({
        type: 'COMPLETE_SETUP',
        payload: {
          vectorDatabaseLocation: '/Users/user/Documents/zohar-assistant/vector_db',
          localEndpoint: 'http://localhost:8000'
        }
      });
    };

    if (!state.setupComplete) {
      completeSetup();
    }
  }, [dispatch, state.setupComplete]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const openLocation = (path: string) => {
    // In a real Tauri app, this would open the file manager
    console.log('Opening:', path);
  };

  const openEndpoint = (url: string) => {
    // In a real Tauri app, this would open the browser
    window.open(url, '_blank');
  };

  const configuredPlatforms = Object.keys(platformCredentials).filter(
    platform => platformCredentials[platform]?.configured
  );

  const enabledActions = Object.keys(selectedActions).filter(
    action => selectedActions[action]
  );

  const totalDocuments = fileProcessingStatus.vectorDatabases.reduce((sum, db) => sum + db.documents, 0);

  if (!state.setupComplete) {
    return (
      <WizardLayout 
        title="Finalizing Setup"
        subtitle="Completing your assistant configuration..."
        showProgress={false}
      >
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-primary-600 border-t-transparent rounded-full animate-spin mx-auto mb-6"></div>
          <p className="text-lg text-gray-600">
            Setting up your assistant with the configured options...
          </p>
        </div>
      </WizardLayout>
    );
  }

  return (
    <WizardLayout 
      title="Setup Complete!"
      subtitle="Your personal assistant is ready to use"
      showProgress={false}
    >
      <div className="space-y-8">
        {/* Success Header */}
        <div className="text-center">
          <div className="w-24 h-24 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle className="w-12 h-12 text-green-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            🎉 Zohar Assistant is Ready!
          </h2>
          <p className="text-lg text-gray-600">
            Your intelligent personal assistant has been successfully configured and is running.
          </p>
        </div>

        {/* Configuration Summary */}
        <div className="grid md:grid-cols-2 gap-6">
          {/* Left Column */}
          <div className="space-y-4">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h3 className="font-semibold text-blue-900 mb-3">Features Enabled</h3>
              <div className="space-y-2">
                {selectedFeatures.emailProcessing && (
                  <div className="flex items-center space-x-2">
                    <CheckCircle className="w-4 h-4 text-green-600" />
                    <span className="text-sm text-blue-800">Email Auto-Processing</span>
                  </div>
                )}
                {selectedFeatures.customMCP && (
                  <div className="flex items-center space-x-2">
                    <CheckCircle className="w-4 h-4 text-green-600" />
                    <span className="text-sm text-blue-800">Custom MCP Servers</span>
                  </div>
                )}
                {selectedFeatures.personalBot && (
                  <div className="flex items-center space-x-2">
                    <CheckCircle className="w-4 h-4 text-green-600" />
                    <span className="text-sm text-blue-800">Personal Bot Assistant</span>
                  </div>
                )}
              </div>
            </div>

            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <h3 className="font-semibold text-green-900 mb-3">Platforms Connected</h3>
              {configuredPlatforms.length > 0 ? (
                <div className="space-y-2">
                  {configuredPlatforms.map(platform => (
                    <div key={platform} className="flex items-center space-x-2">
                      <CheckCircle className="w-4 h-4 text-green-600" />
                      <span className="text-sm text-green-800 capitalize">{platform}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-green-700">No platforms configured (can be added later)</p>
              )}
            </div>
          </div>

          {/* Right Column */}
          <div className="space-y-4">
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
              <h3 className="font-semibold text-purple-900 mb-3">Knowledge Base</h3>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-purple-700">Databases:</span>
                  <span className="text-sm font-medium text-purple-900">
                    {fileProcessingStatus.vectorDatabases.length}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-purple-700">Documents:</span>
                  <span className="text-sm font-medium text-purple-900">
                    {totalDocuments.toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-purple-700">Files Processed:</span>
                  <span className="text-sm font-medium text-purple-900">
                    {fileProcessingStatus.processedFiles}
                  </span>
                </div>
              </div>
            </div>

            <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
              <h3 className="font-semibold text-indigo-900 mb-3">Privacy Settings</h3>
              <div className="flex items-center space-x-2">
                {botSettings.type === 'private' ? (
                  <>
                    <CheckCircle className="w-4 h-4 text-green-600" />
                    <span className="text-sm text-indigo-800">Private Mode - Full Data Access</span>
                  </>
                ) : (
                  <>
                    <Globe className="w-4 h-4 text-blue-600" />
                    <span className="text-sm text-indigo-800">Public Mode - Privacy Protected</span>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Access Information */}
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Access Your Assistant</h3>
          
          <div className="grid md:grid-cols-2 gap-6">
            {/* Local Endpoint */}
            <div>
              <h4 className="font-medium text-gray-900 mb-2">Web Interface</h4>
              <div className="flex items-center space-x-2 p-3 bg-white border rounded-lg">
                <Globe className="w-5 h-5 text-gray-500" />
                <code className="flex-1 text-sm font-mono text-gray-700">
                  {localEndpoint}
                </code>
                <button
                  onClick={() => copyToClipboard(localEndpoint!)}
                  className="text-gray-500 hover:text-gray-700"
                  title="Copy URL"
                >
                  <Copy className="w-4 h-4" />
                </button>
                <button
                  onClick={() => openEndpoint(localEndpoint!)}
                  className="text-primary-600 hover:text-primary-700"
                  title="Open in browser"
                >
                  <ExternalLink className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Database Location */}
            <div>
              <h4 className="font-medium text-gray-900 mb-2">Vector Database</h4>
              <div className="flex items-center space-x-2 p-3 bg-white border rounded-lg">
                <Folder className="w-5 h-5 text-gray-500" />
                <code className="flex-1 text-sm font-mono text-gray-700 truncate">
                  {vectorDatabaseLocation}
                </code>
                <button
                  onClick={() => copyToClipboard(vectorDatabaseLocation!)}
                  className="text-gray-500 hover:text-gray-700"
                  title="Copy path"
                >
                  <Copy className="w-4 h-4" />
                </button>
                <button
                  onClick={() => openLocation(vectorDatabaseLocation!)}
                  className="text-primary-600 hover:text-primary-700"
                  title="Open folder"
                >
                  <Folder className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Next Steps */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-4">Next Steps</h3>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <h4 className="font-medium text-blue-900 mb-2">Get Started</h4>
              <ul className="text-sm text-blue-700 space-y-1">
                <li>• Open the web interface to start chatting</li>
                <li>• Try asking questions about your documents</li>
                <li>• Test the enabled features and actions</li>
                <li>• Explore the knowledge base search</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium text-blue-900 mb-2">Customize Further</h4>
              <ul className="text-sm text-blue-700 space-y-1">
                <li>• Add more platform connections</li>
                <li>• Enable additional actions</li>
                <li>• Process more files and folders</li>
                <li>• Adjust privacy and bot settings</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-center space-x-4">
          <button
            onClick={() => openEndpoint(localEndpoint!)}
            className="btn-primary flex items-center space-x-2"
          >
            <Globe className="w-5 h-5" />
            <span>Open Assistant</span>
          </button>
          
          <button
            onClick={() => window.close()}
            className="btn-secondary flex items-center space-x-2"
          >
            <Settings className="w-5 h-5" />
            <span>Close Setup</span>
          </button>
        </div>

        {/* Support Information */}
        <div className="text-center text-sm text-gray-500">
          <p>
            Need help? Check the documentation or contact support for assistance.
          </p>
        </div>
      </div>
    </WizardLayout>
  );
} 