import React from 'react';
import { WizardProvider, useWizard } from './context/WizardContext';
import { 
  WelcomeStep, 
  FeaturesStep, 
  PlatformsStep, 
  ActionsStep, 
  FilesStep, 
  DatabasesStep, 
  BotSettingsStep, 
  CompleteStep 
} from './components/steps';
import './App.css';

function WizardRouter() {
  const { state } = useWizard();
  
  const steps = [
    <WelcomeStep />,
    <FeaturesStep />,
    <PlatformsStep />,
    <ActionsStep />,
    <FilesStep />,
    <DatabasesStep />,
    <BotSettingsStep />,
    <CompleteStep />
  ];

  return steps[state.currentStep] || <WelcomeStep />;
}

function App() {
  return (
    <WizardProvider>
      <div className="App">
        <WizardRouter />
      </div>
    </WizardProvider>
  );
}

export default App;
