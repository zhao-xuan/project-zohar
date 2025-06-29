# Zohar Assistant Setup Wizard

A beautiful, modern desktop application built with Tauri + React for setting up your personal AI assistant with advanced file processing, email automation, and vector database creation.

## 🎯 Features

### Multi-Step Wizard Setup
- **Welcome Screen**: Overview of capabilities and features
- **Feature Selection**: Choose Email Processing, Custom MCP Servers, Personal Bot
- **Platform Configuration**: Setup Gmail, Outlook, OpenAI, Anthropic integrations
- **Action Selection**: Enable specific AI actions and automations
- **File Processing**: Drag & drop files/folders with real-time progress tracking
- **Database Review**: Examine dynamically generated vector database structures
- **Privacy Settings**: Choose between Private (full access) or Public (tone-only) modes
- **Setup Completion**: Final configuration summary and access information

### Advanced File Processing
- **Drag & Drop Interface**: Intuitive file and folder selection
- **Multi-Format Support**: PDF, Word, Excel, Images, Audio, Video, Text files
- **Real-Time Progress**: Live progress tracking with error handling
- **Dynamic Schema Generation**: Automatic database structure creation based on content
- **Vector Database Creation**: Optimized searchable knowledge bases

### Platform Integrations
- **Google Gmail**: OAuth2 authentication and email processing
- **Microsoft Outlook**: Azure AD integration
- **OpenAI API**: Advanced AI capabilities
- **Anthropic Claude**: Alternative AI model support
- **Custom MCP Servers**: Extensible integration framework

### Privacy & Security
- **Local Processing**: All data stays on your device
- **Private Mode**: Full document indexing and search
- **Public Mode**: Tone mimicking without personal data storage
- **Encrypted Storage**: Secure vector database storage
- **User Control**: Switch modes anytime, complete data ownership

## 🛠 Technology Stack

- **Frontend**: React 18 + TypeScript
- **Desktop**: Tauri 2.0 (Rust backend)
- **Styling**: Tailwind CSS with custom components
- **State Management**: React Context + useReducer
- **File Handling**: react-dropzone
- **Icons**: Lucide React
- **Build Tool**: Vite

## 🚀 Getting Started

### Prerequisites
- Node.js 18+ and npm
- Rust 1.70+
- Tauri CLI 2.0+

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd zohar-setup-wizard
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Development mode**
   ```bash
   npm run tauri dev
   ```

4. **Build for production**
   ```bash
   npm run tauri build
   ```

## 📱 Application Flow

```
1. Welcome → 2. Features → 3. Platforms → 4. Actions
                    ↓
8. Complete ← 7. Bot Settings ← 6. Databases ← 5. Files
```

### Step Details

#### 1. Welcome Screen
- Introduction to Zohar Assistant
- Feature overview with icons and descriptions
- Setup time estimation

#### 2. Feature Selection
- Email Auto-Processing toggle
- Custom MCP Servers toggle  
- Personal Bot Assistant toggle
- Dynamic UI based on selections

#### 3. Platform Setup
- Platform-specific authentication guides
- File upload for OAuth credentials
- API key input with secure handling
- Configuration validation

#### 4. Action Selection
- Categorized action list (Email, MCP, AI Enhancement)
- Platform dependency checking
- Real-time availability updates

#### 5. File Processing
- Drag & drop interface
- Multi-file and folder selection
- Real-time processing with progress bars
- Error handling and reporting
- Mock vector database generation

#### 6. Database Review
- Expandable database cards
- Schema structure visualization
- Document count and statistics
- Sample query examples
- Technical implementation details

#### 7. Bot Configuration
- Private vs Public mode selection
- Privacy settings configuration
- Feature impact explanation
- Security guarantees

#### 8. Setup Completion
- Configuration summary
- Access information (URL, database path)
- Next steps guidance
- Quick action buttons

## 🎨 UI/UX Features

### Design System
- **Color Palette**: Primary blue theme with semantic colors
- **Typography**: Clear hierarchy with multiple font weights
- **Animations**: Smooth transitions and micro-interactions
- **Responsive**: Works on various screen sizes
- **Accessibility**: Keyboard navigation and screen reader support

### Interactive Elements
- **Progress Sidebar**: Real-time step tracking and file processing status
- **Feature Cards**: Clickable selection with visual feedback
- **Form Validation**: Real-time input validation and error display
- **Loading States**: Progress indicators and skeleton screens
- **Success States**: Confirmation animations and checkmarks

### Advanced Components
- **Drag & Drop Zone**: Visual feedback for file operations
- **Expandable Panels**: Database schema exploration
- **Toggle Switches**: Privacy and feature settings
- **Code Blocks**: Copyable paths and URLs
- **Status Indicators**: Processing states and errors

## 🔧 Configuration

### Environment Variables
```env
# Optional: Backend integration
VITE_BACKEND_URL=http://localhost:8000
VITE_API_ENDPOINT=/api/v1

# Development
VITE_DEV_MODE=true
```

### Tauri Configuration
The app uses Tauri's security features:
- File system access (for file processing)
- Window management (for optimal UX)
- System integration (for opening folders/URLs)

## 🧪 Development

### Project Structure
```
src/
├── components/          # React components
│   ├── steps/          # Wizard step components
│   ├── ProgressSidebar.tsx
│   └── WizardLayout.tsx
├── context/            # React Context providers
│   └── WizardContext.tsx
├── types/              # TypeScript definitions
│   └── wizard.ts
├── App.tsx             # Main application
└── main.tsx           # Entry point
```

### Adding New Steps
1. Create component in `src/components/steps/`
2. Add to `steps/index.ts` exports
3. Update `WizardContext.tsx` step definitions
4. Add to `App.tsx` router array

### Customizing Styles
- Edit `src/App.css` for custom Tailwind classes
- Modify `tailwind.config.js` for theme customization
- Component-specific styles in individual files

## 🤝 Integration

### Backend Integration
The wizard can integrate with the main Zohar Assistant backend:

```typescript
// Example API calls
const processFiles = async (files: File[]) => {
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));
  
  const response = await fetch('/api/process-files', {
    method: 'POST',
    body: formData
  });
  
  return response.json();
};
```

### Data Persistence
Configuration is saved to:
- **Windows**: `%APPDATA%/zohar-assistant/config.json`
- **macOS**: `~/Library/Application Support/zohar-assistant/config.json`
- **Linux**: `~/.config/zohar-assistant/config.json`

## 📦 Building & Distribution

### Development Build
```bash
npm run tauri dev
```

### Production Build
```bash
npm run tauri build
```

### Platform-Specific Builds
```bash
# macOS
npm run tauri build -- --target universal-apple-darwin

# Windows  
npm run tauri build -- --target x86_64-pc-windows-msvc

# Linux
npm run tauri build -- --target x86_64-unknown-linux-gnu
```

## 🐛 Troubleshooting

### Common Issues

1. **Build Errors**
   - Ensure Rust toolchain is up to date
   - Clear `node_modules` and reinstall
   - Check Tauri CLI version compatibility

2. **File Processing Issues**
   - Verify file permissions
   - Check supported file types
   - Monitor browser console for errors

3. **Platform Integration**
   - Validate API credentials format
   - Check network connectivity
   - Review authentication scopes

## 📄 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

---

Built with ❤️ using Tauri + React for the Zohar Assistant ecosystem.
