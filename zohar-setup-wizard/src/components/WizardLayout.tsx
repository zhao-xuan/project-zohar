import React from 'react';
import { ProgressSidebar } from './ProgressSidebar';

interface WizardLayoutProps {
  children: React.ReactNode;
  title: string;
  subtitle?: string;
  showProgress?: boolean;
}

export function WizardLayout({ 
  children, 
  title, 
  subtitle, 
  showProgress = true 
}: WizardLayoutProps) {
  return (
    <div className="wizard-container relative">
      {/* Progress Sidebar */}
      {showProgress && <ProgressSidebar />}
      
      {/* Main Content */}
      <div className="flex items-center justify-center min-h-screen p-6">
        <div className="wizard-card animate-fade-in">
          <div className="wizard-header">
            <h1 className="wizard-title">{title}</h1>
            {subtitle && <p className="wizard-subtitle">{subtitle}</p>}
          </div>
          
          <div className="wizard-content">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
} 