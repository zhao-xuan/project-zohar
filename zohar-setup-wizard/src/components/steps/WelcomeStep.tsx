import React from 'react';
import { ArrowRight, Bot, Mail, Server, Database, FileText, Shield } from 'lucide-react';
import { useWizard } from '../../context/WizardContext';
import { WizardLayout } from '../WizardLayout';

export function WelcomeStep() {
  const { nextStep } = useWizard();

  const features = [
    {
      icon: <Mail className="w-8 h-8 text-blue-600" />,
      title: 'Email Auto-Processing',
      description: 'Automatically process and analyze emails from Gmail, Outlook, and other platforms'
    },
    {
      icon: <Server className="w-8 h-8 text-green-600" />,
      title: 'Custom MCP Servers',
      description: 'Connect and configure custom Model Context Protocol servers for extended functionality'
    },
    {
      icon: <Bot className="w-8 h-8 text-purple-600" />,
      title: 'Personal Bot Assistant',
      description: 'Set up your AI assistant with personalized knowledge and capabilities'
    },
    {
      icon: <FileText className="w-8 h-8 text-orange-600" />,
      title: 'Intelligent File Processing',
      description: 'Process and index various file formats with advanced AI-powered analysis'
    },
    {
      icon: <Database className="w-8 h-8 text-red-600" />,
      title: 'Vector Database Integration',
      description: 'Automatically generate optimized vector databases for semantic search'
    },
    {
      icon: <Shield className="w-8 h-8 text-indigo-600" />,
      title: 'Privacy Controls',
      description: 'Choose between private mode (full indexing) or public mode (tone mimicking only)'
    }
  ];

  return (
    <WizardLayout 
      title="Welcome to Zohar Assistant Setup"
      subtitle="Let's configure your personal AI assistant with powerful automation and intelligence features"
      showProgress={false}
    >
      <div className="space-y-8">
        {/* Hero Section */}
        <div className="text-center">
          <div className="mx-auto w-24 h-24 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center mb-6">
            <Bot className="w-12 h-12 text-white" />
          </div>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            This setup wizard will guide you through configuring your personal assistant with 
            advanced features including email processing, file analysis, and intelligent automation.
          </p>
        </div>

        {/* Features Grid */}
        <div className="grid md:grid-cols-2 gap-6">
          {features.map((feature, index) => (
            <div 
              key={index}
              className="bg-gray-50 rounded-lg p-6 hover:bg-gray-100 transition-colors duration-200"
            >
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0">
                  {feature.icon}
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-gray-600">
                    {feature.description}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Setup Time Estimate */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
              <ArrowRight className="w-4 h-4 text-blue-600" />
            </div>
            <div>
              <h4 className="text-lg font-semibold text-blue-900">Quick Setup</h4>
              <p className="text-blue-700">
                Setup typically takes 5-10 minutes depending on the features you choose to configure.
              </p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <div className="wizard-navigation">
          <div></div> {/* Empty div for spacing */}
          <button
            onClick={nextStep}
            className="btn-primary flex items-center space-x-2"
          >
            <span>Get Started</span>
            <ArrowRight className="w-5 h-5" />
          </button>
        </div>
      </div>
    </WizardLayout>
  );
} 