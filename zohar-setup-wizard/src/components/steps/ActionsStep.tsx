import React from 'react';
import { ArrowLeft, ArrowRight, Check, AlertCircle } from 'lucide-react';
import { useWizard } from '../../context/WizardContext';
import { WizardLayout } from '../WizardLayout';
import { AvailableAction } from '../../types/wizard';

export function ActionsStep() {
  const { state, dispatch, nextStep, previousStep } = useWizard();
  const { selectedFeatures, platformCredentials, selectedActions } = state;

  const availableActions: AvailableAction[] = [
    // Email Actions
    {
      id: 'email-categorization',
      name: 'Email Categorization',
      description: 'Automatically categorize incoming emails based on content and sender',
      category: 'Email Processing',
      requiredPlatforms: ['gmail', 'outlook'],
      enabled: selectedFeatures.emailProcessing
    },
    {
      id: 'smart-replies',
      name: 'Smart Reply Suggestions',
      description: 'Generate intelligent reply suggestions for emails',
      category: 'Email Processing',
      requiredPlatforms: ['gmail', 'outlook'],
      enabled: selectedFeatures.emailProcessing
    },
    {
      id: 'email-summarization',
      name: 'Email Summarization',
      description: 'Create summaries of long email threads and conversations',
      category: 'Email Processing',
      requiredPlatforms: ['gmail', 'outlook'],
      enabled: selectedFeatures.emailProcessing
    },
    
    // MCP Server Actions
    {
      id: 'custom-tool-integration',
      name: 'Custom Tool Integration',
      description: 'Connect to external tools and APIs through MCP servers',
      category: 'MCP Integration',
      requiredPlatforms: [],
      enabled: selectedFeatures.customMCP
    },
    {
      id: 'workflow-automation',
      name: 'Workflow Automation',
      description: 'Automate complex workflows across multiple services',
      category: 'MCP Integration',
      requiredPlatforms: [],
      enabled: selectedFeatures.customMCP
    },
    
    // Personal Bot Actions
    {
      id: 'document-qa',
      name: 'Document Q&A',
      description: 'Answer questions based on your uploaded documents',
      category: 'Personal Assistant',
      requiredPlatforms: [],
      enabled: selectedFeatures.personalBot
    },
    {
      id: 'context-memory',
      name: 'Contextual Memory',
      description: 'Remember previous conversations and maintain context',
      category: 'Personal Assistant',
      requiredPlatforms: [],
      enabled: selectedFeatures.personalBot
    },
    {
      id: 'task-scheduling',
      name: 'Task Scheduling',
      description: 'Schedule and remind about tasks and appointments',
      category: 'Personal Assistant',
      requiredPlatforms: [],
      enabled: selectedFeatures.personalBot
    },
    
    // AI Enhancement Actions
    {
      id: 'advanced-reasoning',
      name: 'Advanced Reasoning',
      description: 'Enhanced reasoning capabilities using advanced AI models',
      category: 'AI Enhancement',
      requiredPlatforms: ['openai', 'anthropic'],
      enabled: true
    },
    {
      id: 'multimodal-analysis',
      name: 'Multimodal Analysis',
      description: 'Analyze images, documents, and other media types',
      category: 'AI Enhancement',
      requiredPlatforms: ['openai'],
      enabled: true
    }
  ];

  // Filter actions based on enabled features
  const relevantActions = availableActions.filter(action => action.enabled);

  // Group actions by category
  const actionsByCategory = relevantActions.reduce((acc, action) => {
    if (!acc[action.category]) {
      acc[action.category] = [];
    }
    acc[action.category].push(action);
    return acc;
  }, {} as Record<string, AvailableAction[]>);

  const toggleAction = (actionId: string) => {
    dispatch({
      type: 'UPDATE_ACTIONS',
      payload: {
        ...selectedActions,
        [actionId]: !selectedActions[actionId]
      }
    });
  };

  const isActionAvailable = (action: AvailableAction) => {
    if (action.requiredPlatforms.length === 0) return true;
    return action.requiredPlatforms.some(platform => 
      platformCredentials[platform]?.configured
    );
  };

  const selectedCount = Object.values(selectedActions).filter(Boolean).length;

  return (
    <WizardLayout 
      title="Select Actions"
      subtitle="Choose the actions and APIs you want to enable for your assistant"
    >
      <div className="space-y-6">
        {/* Actions by Category */}
        {Object.entries(actionsByCategory).map(([category, actions]) => (
          <div key={category} className="space-y-4">
            <h3 className="text-xl font-semibold text-gray-900 border-b border-gray-200 pb-2">
              {category}
            </h3>
            
            <div className="grid gap-4">
              {actions.map((action) => {
                const isSelected = selectedActions[action.id];
                const isAvailable = isActionAvailable(action);
                const missingPlatforms = action.requiredPlatforms.filter(
                  platform => !platformCredentials[platform]?.configured
                );

                return (
                  <div
                    key={action.id}
                    onClick={() => isAvailable && toggleAction(action.id)}
                    className={`border rounded-lg p-4 transition-all duration-200 ${
                      !isAvailable 
                        ? 'border-gray-200 bg-gray-50 cursor-not-allowed opacity-60'
                        : isSelected
                        ? 'border-primary-500 bg-primary-50 cursor-pointer'
                        : 'border-gray-200 hover:border-primary-300 hover:shadow-sm cursor-pointer'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-2">
                          <h4 className="text-lg font-semibold text-gray-900">
                            {action.name}
                          </h4>
                          {isSelected && isAvailable && (
                            <div className="w-5 h-5 bg-primary-600 rounded-full flex items-center justify-center">
                              <Check className="w-3 h-3 text-white" />
                            </div>
                          )}
                        </div>
                        
                        <p className="text-gray-600 mb-3">
                          {action.description}
                        </p>

                        {/* Required Platforms */}
                        {action.requiredPlatforms.length > 0 && (
                          <div className="flex items-center space-x-2">
                            <span className="text-sm text-gray-500">Requires:</span>
                            <div className="flex space-x-1">
                              {action.requiredPlatforms.map(platform => (
                                <span
                                  key={platform}
                                  className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                                    platformCredentials[platform]?.configured
                                      ? 'bg-green-100 text-green-800'
                                      : 'bg-red-100 text-red-800'
                                  }`}
                                >
                                  {platform}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Warning for missing platforms */}
                        {!isAvailable && missingPlatforms.length > 0 && (
                          <div className="flex items-center space-x-2 mt-2 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                            <AlertCircle className="w-4 h-4 text-yellow-600 flex-shrink-0" />
                            <span className="text-sm text-yellow-800">
                              Configure {missingPlatforms.join(', ')} to enable this action
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}

        {/* Selection Summary */}
        {selectedCount > 0 && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <p className="text-green-800">
              <span className="font-semibold">{selectedCount}</span> action{selectedCount !== 1 ? 's' : ''} selected. 
              These will be available once setup is complete.
            </p>
          </div>
        )}

        {/* Skip Option */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-blue-800">
            <strong>Note:</strong> You can enable or disable actions later through the settings panel. 
            Actions requiring platform authentication will only work with properly configured credentials.
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