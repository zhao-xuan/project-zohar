import React, { useState } from 'react';
import { ArrowLeft, ArrowRight, Check, Upload, Eye, EyeOff, ExternalLink } from 'lucide-react';
import { useWizard } from '../../context/WizardContext';
import { WizardLayout } from '../WizardLayout';
import { AvailablePlatform } from '../../types/wizard';

export function PlatformsStep() {
  const { state, dispatch, nextStep, previousStep } = useWizard();
  const { selectedFeatures, platformCredentials } = state;
  const [showCredentials, setShowCredentials] = useState<Record<string, boolean>>({});

  const availablePlatforms: AvailablePlatform[] = [
    {
      id: 'gmail',
      name: 'Gmail',
      description: 'Google Gmail integration for email processing',
      icon: '📧',
      authType: 'file',
      instructions: `To connect Gmail:
1. Go to Google Cloud Console (console.cloud.google.com)
2. Create a new project or select existing one
3. Enable Gmail API
4. Create credentials (OAuth 2.0 Client ID)
5. Download the credentials.json file
6. Upload the file below`
    },
    {
      id: 'outlook',
      name: 'Microsoft Outlook',
      description: 'Microsoft Outlook/Hotmail integration',
      icon: '📮',
      authType: 'file',
      instructions: `To connect Outlook:
1. Go to Azure Portal (portal.azure.com)
2. Register a new application
3. Configure Mail.Read permissions
4. Generate client secret
5. Download the configuration file
6. Upload the file below`
    },
    {
      id: 'openai',
      name: 'OpenAI',
      description: 'OpenAI API for enhanced AI capabilities',
      icon: '🤖',
      authType: 'apikey',
      instructions: `To connect OpenAI:
1. Go to OpenAI Platform (platform.openai.com)
2. Navigate to API Keys section
3. Create a new API key
4. Copy and paste the key below`
    },
    {
      id: 'anthropic',
      name: 'Anthropic',
      description: 'Anthropic Claude API integration',
      icon: '🧠',
      authType: 'apikey',
      instructions: `To connect Anthropic:
1. Go to Anthropic Console (console.anthropic.com)
2. Navigate to API Keys
3. Create a new API key
4. Copy and paste the key below`
    }
  ];

  // Filter platforms based on selected features
  const relevantPlatforms = availablePlatforms.filter(platform => {
    if (platform.id === 'gmail' || platform.id === 'outlook') {
      return selectedFeatures.emailProcessing;
    }
    return true; // Show AI platforms for all features
  });

  const updateCredentials = (platformId: string, type: 'file' | 'text', value: string | File) => {
    dispatch({
      type: 'UPDATE_CREDENTIALS',
      payload: {
        platform: platformId,
        credentials: {
          type,
          value,
          configured: true
        }
      }
    });
  };

  const handleFileUpload = (platformId: string, file: File) => {
    updateCredentials(platformId, 'file', file);
  };

  const handleTextInput = (platformId: string, text: string) => {
    updateCredentials(platformId, 'text', text);
  };

  const toggleShowCredentials = (platformId: string) => {
    setShowCredentials(prev => ({
      ...prev,
      [platformId]: !prev[platformId]
    }));
  };

  const configuredCount = Object.keys(platformCredentials).filter(
    platform => platformCredentials[platform]?.configured
  ).length;

  return (
    <WizardLayout 
      title="Platform Setup"
      subtitle="Configure your platform credentials and API connections"
    >
      <div className="space-y-6">
        {/* Platforms */}
        <div className="space-y-6">
          {relevantPlatforms.map((platform) => {
            const isConfigured = platformCredentials[platform.id]?.configured;
            const credentials = platformCredentials[platform.id];

            return (
              <div key={platform.id} className="border border-gray-200 rounded-lg overflow-hidden">
                {/* Platform Header */}
                <div className={`p-6 ${isConfigured ? 'bg-green-50' : 'bg-gray-50'}`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <span className="text-2xl">{platform.icon}</span>
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900">
                          {platform.name}
                        </h3>
                        <p className="text-gray-600">
                          {platform.description}
                        </p>
                      </div>
                    </div>
                    {isConfigured && (
                      <div className="flex items-center space-x-2 text-green-600">
                        <Check className="w-5 h-5" />
                        <span className="font-medium">Configured</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Configuration Section */}
                <div className="p-6 border-t border-gray-200">
                  {/* Instructions */}
                  <details className="mb-4">
                    <summary className="cursor-pointer flex items-center space-x-2 text-primary-600 hover:text-primary-700">
                      <ExternalLink className="w-4 h-4" />
                      <span>Setup Instructions</span>
                    </summary>
                    <div className="mt-3 p-4 bg-blue-50 rounded-lg">
                      <pre className="text-sm text-gray-700 whitespace-pre-wrap">
                        {platform.instructions}
                      </pre>
                    </div>
                  </details>

                  {/* Configuration Input */}
                  {platform.authType === 'file' ? (
                    <div className="form-group">
                      <label className="form-label">Upload Credentials File</label>
                      <div className="flex items-center space-x-3">
                        <input
                          type="file"
                          accept=".json,.txt"
                          onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file) {
                              handleFileUpload(platform.id, file);
                            }
                          }}
                          className="form-input"
                        />
                        <Upload className="w-5 h-5 text-gray-400" />
                      </div>
                      {credentials?.type === 'file' && credentials.value instanceof File && (
                        <p className="text-sm text-green-600 mt-2">
                          ✓ File uploaded: {credentials.value.name}
                        </p>
                      )}
                    </div>
                  ) : (
                    <div className="form-group">
                      <label className="form-label">API Key</label>
                      <div className="relative">
                        <input
                          type={showCredentials[platform.id] ? 'text' : 'password'}
                          placeholder="Enter your API key..."
                          value={credentials?.type === 'text' ? (credentials.value as string) : ''}
                          onChange={(e) => handleTextInput(platform.id, e.target.value)}
                          className="form-input pr-10"
                        />
                        <button
                          type="button"
                          onClick={() => toggleShowCredentials(platform.id)}
                          className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                        >
                          {showCredentials[platform.id] ? 
                            <EyeOff className="w-5 h-5" /> : 
                            <Eye className="w-5 h-5" />
                          }
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Configuration Summary */}
        {configuredCount > 0 && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <p className="text-green-800">
              <span className="font-semibold">{configuredCount}</span> platform{configuredCount !== 1 ? 's' : ''} configured. 
              You can add more connections later in settings.
            </p>
          </div>
        )}

        {/* Skip Option */}
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-yellow-800">
            <strong>Optional:</strong> You can skip platform setup for now and configure connections later. 
            Some features may have limited functionality without proper authentication.
          </p>
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