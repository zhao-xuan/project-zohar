export interface WizardStep {
  id: string;
  title: string;
  description: string;
  completed: boolean;
}

export interface SelectedFeatures {
  emailProcessing: boolean;
  customMCP: boolean;
  personalBot: boolean;
}

export interface PlatformCredentials {
  [platform: string]: {
    type: 'file' | 'text';
    value: string | File;
    configured: boolean;
  };
}

export interface SelectedActions {
  [actionId: string]: boolean;
}

export interface FileProcessingStatus {
  isProcessing: boolean;
  progress: number;
  currentFile?: string;
  totalFiles: number;
  processedFiles: number;
  errors: string[];
  vectorDatabases: VectorDatabase[];
}

export interface VectorDatabase {
  id: string;
  name: string;
  documents: number;
  structure: DatabaseSchema;
  path: string;
}

export interface DatabaseSchema {
  [field: string]: {
    type: string;
    description: string;
  };
}

export interface BotSettings {
  type: 'private' | 'public';
  privateSettings?: {
    indexEntireDatabase: boolean;
  };
  publicSettings?: {
    mimicToneOnly: boolean;
    excludePersonalData: boolean;
  };
}

export interface WizardState {
  currentStep: number;
  selectedFeatures: SelectedFeatures;
  platformCredentials: PlatformCredentials;
  selectedActions: SelectedActions;
  fileProcessingStatus: FileProcessingStatus;
  botSettings: BotSettings;
  setupComplete: boolean;
  vectorDatabaseLocation?: string;
  localEndpoint?: string;
}

export interface AvailablePlatform {
  id: string;
  name: string;
  description: string;
  icon: string;
  authType: 'oauth' | 'apikey' | 'file';
  instructions: string;
}

export interface AvailableAction {
  id: string;
  name: string;
  description: string;
  category: string;
  requiredPlatforms: string[];
  enabled: boolean;
} 