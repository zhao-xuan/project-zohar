import React from 'react';
import { ArrowLeft, ArrowRight, Mail, Server, Bot, Check } from 'lucide-react';
import { useWizard } from '../../context/WizardContext';
import { WizardLayout } from '../WizardLayout';

export function FeaturesStep() {
  const { state, dispatch, nextStep, previousStep } = useWizard();
  const { selectedFeatures } = state;

  const features = [
    {
      id: 'emailProcessing' as keyof typeof selectedFeatures,
      icon: <Mail className="w-12 h-12" />,
      title: 'Email Auto-Processing',
      description: 'Automatically process emails from Gmail, Outlook, and other platforms. Extract insights, categorize, and respond intelligently.',
      benefits: [
        'Automatic email categorization',
        'Smart response suggestions',
        'Priority inbox management',
        'Email sentiment analysis'
      ]
    },
    {
      id: 'customMCP' as keyof typeof selectedFeatures,
      icon: <Server className="w-12 h-12" />,
      title: 'Custom MCP Servers',
      description: 'Connect to Model Context Protocol servers for extended functionality. Integrate with your existing tools and workflows.',
      benefits: [
        'Extended API integrations',
        'Custom tool connections',
        'Workflow automation',
        'Third-party service access'
      ]
    },
    {
      id: 'personalBot' as keyof typeof selectedFeatures,
      icon: <Bot className="w-12 h-12" />,
      title: 'Personal Bot Assistant',
      description: 'Your AI assistant with personalized knowledge base. Process your files and chat history for contextual conversations.',
      benefits: [
        'Personalized responses',
        'Document knowledge base',
        'Chat history integration',
        'Context-aware assistance'
      ]
    }
  ];

  const toggleFeature = (featureId: keyof typeof selectedFeatures) => {
    dispatch({
      type: 'UPDATE_FEATURES',
      payload: {
        [featureId]: !selectedFeatures[featureId]
      }
    });
  };

  const selectedCount = Object.values(selectedFeatures).filter(Boolean).length;
  const canProceed = selectedCount > 0;

  return (
    <WizardLayout 
      title="Select Features"
      subtitle="Choose the functionalities you want to set up for your assistant"
    >
      <div className="space-y-6">
        {/* Features Grid */}
        <div className="grid gap-6">
          {features.map((feature) => {
            const isSelected = selectedFeatures[feature.id];
            return (
              <div
                key={feature.id}
                onClick={() => toggleFeature(feature.id)}
                className={`feature-card ${isSelected ? 'selected' : ''}`}
              >
                <div className="flex items-start space-x-4">
                  <div className={`flex-shrink-0 ${isSelected ? 'text-primary-600' : 'text-gray-400'}`}>
                    {feature.icon}
                  </div>
                  
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-xl font-semibold text-gray-900">
                        {feature.title}
                      </h3>
                      {isSelected && (
                        <div className="w-6 h-6 bg-primary-600 rounded-full flex items-center justify-center">
                          <Check className="w-4 h-4 text-white" />
                        </div>
                      )}
                    </div>
                    
                    <p className="text-gray-600 mb-4">
                      {feature.description}
                    </p>
                    
                    <div className="grid md:grid-cols-2 gap-2">
                      {feature.benefits.map((benefit, index) => (
                        <div key={index} className="flex items-center space-x-2">
                          <div className={`w-2 h-2 rounded-full ${isSelected ? 'bg-primary-400' : 'bg-gray-300'}`} />
                          <span className={`text-sm ${isSelected ? 'text-primary-700' : 'text-gray-500'}`}>
                            {benefit}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Selection Summary */}
        {selectedCount > 0 && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <p className="text-green-800">
              <span className="font-semibold">{selectedCount}</span> feature{selectedCount !== 1 ? 's' : ''} selected. 
              You can change your selection at any time during setup.
            </p>
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
            disabled={!canProceed}
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