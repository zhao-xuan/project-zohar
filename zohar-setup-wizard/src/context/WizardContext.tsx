import React, { createContext, useContext, useReducer, ReactNode } from 'react';
import { WizardState, WizardStep } from '../types/wizard';

interface WizardContextType {
  state: WizardState;
  dispatch: React.Dispatch<WizardAction>;
  nextStep: () => void;
  previousStep: () => void;
  goToStep: (step: number) => void;
  wizardSteps: WizardStep[];
}

type WizardAction =
  | { type: 'SET_STEP'; payload: number }
  | { type: 'NEXT_STEP' }
  | { type: 'PREVIOUS_STEP' }
  | { type: 'UPDATE_FEATURES'; payload: Partial<WizardState['selectedFeatures']> }
  | { type: 'UPDATE_CREDENTIALS'; payload: { platform: string; credentials: any } }
  | { type: 'UPDATE_ACTIONS'; payload: WizardState['selectedActions'] }
  | { type: 'UPDATE_FILE_PROCESSING'; payload: Partial<WizardState['fileProcessingStatus']> }
  | { type: 'UPDATE_BOT_SETTINGS'; payload: Partial<WizardState['botSettings']> }
  | { type: 'COMPLETE_SETUP'; payload: { vectorDatabaseLocation: string; localEndpoint: string } };

const initialState: WizardState = {
  currentStep: 0,
  selectedFeatures: {
    emailProcessing: false,
    customMCP: false,
    personalBot: false,
  },
  platformCredentials: {},
  selectedActions: {},
  fileProcessingStatus: {
    isProcessing: false,
    progress: 0,
    totalFiles: 0,
    processedFiles: 0,
    errors: [],
    vectorDatabases: [],
  },
  botSettings: {
    type: 'private',
    privateSettings: {
      indexEntireDatabase: true,
    },
  },
  setupComplete: false,
};

const wizardSteps: WizardStep[] = [
  {
    id: 'welcome',
    title: 'Welcome',
    description: 'Introduction and overview',
    completed: false,
  },
  {
    id: 'features',
    title: 'Select Features',
    description: 'Choose functionalities to set up',
    completed: false,
  },
  {
    id: 'platforms',
    title: 'Platform Setup',
    description: 'Configure platform credentials',
    completed: false,
  },
  {
    id: 'actions',
    title: 'Select Actions',
    description: 'Choose available APIs and actions',
    completed: false,
  },
  {
    id: 'files',
    title: 'Process Files',
    description: 'Upload and process your data',
    completed: false,
  },
  {
    id: 'databases',
    title: 'Vector Databases',
    description: 'Review generated databases',
    completed: false,
  },
  {
    id: 'bot-settings',
    title: 'Bot Configuration',
    description: 'Configure private/public settings',
    completed: false,
  },
  {
    id: 'complete',
    title: 'Setup Complete',
    description: 'Review final configuration',
    completed: false,
  },
];

function wizardReducer(state: WizardState, action: WizardAction): WizardState {
  switch (action.type) {
    case 'SET_STEP':
      return { ...state, currentStep: action.payload };
    
    case 'NEXT_STEP':
      return { 
        ...state, 
        currentStep: Math.min(state.currentStep + 1, wizardSteps.length - 1) 
      };
    
    case 'PREVIOUS_STEP':
      return { 
        ...state, 
        currentStep: Math.max(state.currentStep - 1, 0) 
      };
    
    case 'UPDATE_FEATURES':
      return {
        ...state,
        selectedFeatures: { ...state.selectedFeatures, ...action.payload },
      };
    
    case 'UPDATE_CREDENTIALS':
      return {
        ...state,
        platformCredentials: {
          ...state.platformCredentials,
          [action.payload.platform]: action.payload.credentials,
        },
      };
    
    case 'UPDATE_ACTIONS':
      return {
        ...state,
        selectedActions: { ...state.selectedActions, ...action.payload },
      };
    
    case 'UPDATE_FILE_PROCESSING':
      return {
        ...state,
        fileProcessingStatus: { ...state.fileProcessingStatus, ...action.payload },
      };
    
    case 'UPDATE_BOT_SETTINGS':
      return {
        ...state,
        botSettings: { ...state.botSettings, ...action.payload },
      };
    
    case 'COMPLETE_SETUP':
      return {
        ...state,
        setupComplete: true,
        vectorDatabaseLocation: action.payload.vectorDatabaseLocation,
        localEndpoint: action.payload.localEndpoint,
      };
    
    default:
      return state;
  }
}

const WizardContext = createContext<WizardContextType | undefined>(undefined);

export function WizardProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(wizardReducer, initialState);

  const nextStep = () => dispatch({ type: 'NEXT_STEP' });
  const previousStep = () => dispatch({ type: 'PREVIOUS_STEP' });
  const goToStep = (step: number) => dispatch({ type: 'SET_STEP', payload: step });

  return (
    <WizardContext.Provider value={{
      state,
      dispatch,
      nextStep,
      previousStep,
      goToStep,
      wizardSteps,
    }}>
      {children}
    </WizardContext.Provider>
  );
}

export function useWizard() {
  const context = useContext(WizardContext);
  if (context === undefined) {
    throw new Error('useWizard must be used within a WizardProvider');
  }
  return context;
} 