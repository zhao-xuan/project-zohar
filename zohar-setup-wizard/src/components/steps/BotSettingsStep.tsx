import React from 'react';
import { ArrowLeft, ArrowRight, Shield, Eye, EyeOff, Lock, Globe } from 'lucide-react';
import { useWizard } from '../../context/WizardContext';
import { WizardLayout } from '../WizardLayout';

export function BotSettingsStep() {
  const { state, dispatch, nextStep, previousStep } = useWizard();
  const { botSettings, fileProcessingStatus } = state;

  const updateBotSettings = (updates: Partial<typeof botSettings>) => {
    dispatch({
      type: 'UPDATE_BOT_SETTINGS',
      payload: updates
    });
  };

  const setBotType = (type: 'private' | 'public') => {
    updateBotSettings({
      type,
      ...(type === 'private' ? {
        privateSettings: {
          indexEntireDatabase: true
        },
        publicSettings: undefined
      } : {
        publicSettings: {
          mimicToneOnly: true,
          excludePersonalData: true
        },
        privateSettings: undefined
      })
    });
  };

  const totalDocuments = fileProcessingStatus.vectorDatabases.reduce((sum, db) => sum + db.documents, 0);

  return (
    <WizardLayout 
      title="Bot Configuration"
      subtitle="Choose how your assistant will handle your data and privacy"
    >
      <div className="space-y-6">
        {/* Mode Selection */}
        <div className="grid md:grid-cols-2 gap-6">
          {/* Private Mode */}
          <div
            onClick={() => setBotType('private')}
            className={`feature-card ${botSettings.type === 'private' ? 'selected' : ''}`}
          >
            <div className="text-center">
              <div className={`w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center ${
                botSettings.type === 'private' ? 'bg-primary-100' : 'bg-gray-100'
              }`}>
                <Lock className={`w-8 h-8 ${
                  botSettings.type === 'private' ? 'text-primary-600' : 'text-gray-400'
                }`} />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">Private Mode</h3>
              <p className="text-gray-600 mb-4">
                Full access to your personal data with complete indexing and search capabilities
              </p>
              
              <div className="text-left space-y-2">
                <h4 className="font-medium text-gray-900">Features:</h4>
                <ul className="text-sm text-gray-600 space-y-1">
                  <li>• Complete document indexing</li>
                  <li>• Full conversation history</li>
                  <li>• Personal context awareness</li>
                  <li>• Private data insights</li>
                  <li>• Detailed search capabilities</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Public Mode */}
          <div
            onClick={() => setBotType('public')}
            className={`feature-card ${botSettings.type === 'public' ? 'selected' : ''}`}
          >
            <div className="text-center">
              <div className={`w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center ${
                botSettings.type === 'public' ? 'bg-primary-100' : 'bg-gray-100'
              }`}>
                <Globe className={`w-8 h-8 ${
                  botSettings.type === 'public' ? 'text-primary-600' : 'text-gray-400'
                }`} />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">Public Mode</h3>
              <p className="text-gray-600 mb-4">
                Tone mimicking only - no personal data storage or detailed indexing
              </p>
              
              <div className="text-left space-y-2">
                <h4 className="font-medium text-gray-900">Features:</h4>
                <ul className="text-sm text-gray-600 space-y-1">
                  <li>• Communication style learning</li>
                  <li>• No personal data retention</li>
                  <li>• General knowledge responses</li>
                  <li>• Privacy-first approach</li>
                  <li>• Safe for public use</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Detailed Settings */}
        {botSettings.type === 'private' && botSettings.privateSettings && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
            <div className="flex items-center space-x-3 mb-4">
              <Shield className="w-6 h-6 text-blue-600" />
              <h3 className="text-lg font-semibold text-blue-900">Private Mode Settings</h3>
            </div>
            
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-white rounded-lg border">
                <div>
                  <h4 className="font-medium text-gray-900">Full Database Indexing</h4>
                  <p className="text-sm text-gray-600">
                    Index all {totalDocuments.toLocaleString()} documents for comprehensive search
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={botSettings.privateSettings.indexEntireDatabase}
                    onChange={(e) => updateBotSettings({
                      privateSettings: {
                        ...botSettings.privateSettings,
                        indexEntireDatabase: e.target.checked
                      }
                    })}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                </label>
              </div>

              <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                <h4 className="font-medium text-green-900 mb-2">Data Security</h4>
                <ul className="text-sm text-green-700 space-y-1">
                  <li>• All data stays on your local machine</li>
                  <li>• No cloud storage or external transmission</li>
                  <li>• Encrypted vector database storage</li>
                  <li>• Complete control over your information</li>
                </ul>
              </div>
            </div>
          </div>
        )}

        {botSettings.type === 'public' && botSettings.publicSettings && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-6">
            <div className="flex items-center space-x-3 mb-4">
              <Shield className="w-6 h-6 text-green-600" />
              <h3 className="text-lg font-semibold text-green-900">Public Mode Settings</h3>
            </div>
            
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-white rounded-lg border">
                <div>
                  <h4 className="font-medium text-gray-900">Mimic Tone Only</h4>
                  <p className="text-sm text-gray-600">
                    Learn your communication style without storing personal content
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={botSettings.publicSettings.mimicToneOnly}
                                       onChange={(e) => updateBotSettings({
                     publicSettings: {
                       mimicToneOnly: e.target.checked,
                       excludePersonalData: botSettings.publicSettings?.excludePersonalData ?? true
                     }
                   })}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-green-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-green-600"></div>
                </label>
              </div>

              <div className="flex items-center justify-between p-4 bg-white rounded-lg border">
                <div>
                  <h4 className="font-medium text-gray-900">Exclude Personal Data</h4>
                  <p className="text-sm text-gray-600">
                    Prevent storage of chat history and personal file content
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={botSettings.publicSettings.excludePersonalData}
                                       onChange={(e) => updateBotSettings({
                     publicSettings: {
                       mimicToneOnly: botSettings.publicSettings?.mimicToneOnly ?? true,
                       excludePersonalData: e.target.checked
                     }
                   })}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-green-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-green-600"></div>
                </label>
              </div>

              <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                <h4 className="font-medium text-yellow-900 mb-2">Limited Functionality</h4>
                <ul className="text-sm text-yellow-700 space-y-1">
                  <li>• No document search capabilities</li>
                  <li>• Cannot reference your personal files</li>
                  <li>• Limited contextual awareness</li>
                  <li>• General responses only</li>
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* Privacy Notice */}
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Privacy & Security</h3>
          <div className="space-y-3">
            <div className="flex items-start space-x-3">
              <Lock className="w-5 h-5 text-gray-600 mt-0.5" />
              <div>
                <h4 className="font-medium text-gray-900">Local Processing</h4>
                <p className="text-sm text-gray-600">
                  All processing happens on your device. No data is sent to external servers.
                </p>
              </div>
            </div>
            <div className="flex items-start space-x-3">
              <Eye className="w-5 h-5 text-gray-600 mt-0.5" />
              <div>
                <h4 className="font-medium text-gray-900">Transparent Operations</h4>
                <p className="text-sm text-gray-600">
                  You can always review, modify, or delete your data and settings.
                </p>
              </div>
            </div>
            <div className="flex items-start space-x-3">
              <Shield className="w-5 h-5 text-gray-600 mt-0.5" />
              <div>
                <h4 className="font-medium text-gray-900">Your Control</h4>
                <p className="text-sm text-gray-600">
                  Switch between private and public modes anytime in settings.
                </p>
              </div>
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
            <span>Complete Setup</span>
            <ArrowRight className="w-5 h-5" />
          </button>
        </div>
      </div>
    </WizardLayout>
  );
} 