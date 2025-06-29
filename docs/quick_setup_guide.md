# Quick Setup Guide

Get your Personal Chatbot System running in under 10 minutes!

## 🚀 One-Command Setup

For the fastest setup experience:

```bash
# Clone and setup everything automatically
git clone <repository-url> personal-chatbot
cd personal-chatbot
make quickstart
```

This will:
- Install all dependencies
- Run the interactive setup wizard  
- Create sample data files
- Index your initial data
- Configure the system for immediate use

## 📋 Manual Setup (Step by Step)

### 1. Install Dependencies
```bash
# Install Python dependencies
make install

# Or manually:
pip install -r requirements.txt
```

### 2. Install Ollama and DeepSeek
```bash
# Automatic installation (macOS)
make ollama-setup

# Or manually:
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull deepseek
```

### 3. Run Setup Wizard
```bash
make setup
```

The wizard will ask you:
- Your name and basic info
- Whether to enable the public bot
- Email integration preferences  
- Data sources to import

### 4. Start Using Your Chatbot

**Terminal Interface:**
```bash
# Personal bot (full access)
make start

# Public bot (restricted)  
make start-public
```

**Web Interface:**
```bash
# Both bots (personal on :5000, public on :5001)
make start-web
```

## ⚡ Quick Commands

Once setup is complete, here are the most useful commands:

```bash
# Start your personal assistant
make start

# Check system health
make check-health  

# Add new documents to your knowledge base
python main.py index-data --source ~/Documents

# Start web interface
make start-web

# View conversation examples
cat examples/conversation_examples.md
```

## 🔧 Configuration

### Essential Files to Customize

1. **`.env`** - Main configuration (created by setup wizard)
2. **`data/personal/bio.txt`** - Your personal information  
3. **`data/personal/tone_examples.txt`** - Your communication style
4. **`data/public/public_bio.txt`** - Public-facing information

### Quick Persona Setup

Edit these files to customize your AI's personality:

```bash
# Edit your personal bio
nano data/personal/bio.txt

# Add examples of your communication style  
nano data/personal/tone_examples.txt

# Set up public information
nano data/public/public_bio.txt
```

## 📧 Email Integration (Optional)

### Gmail Quick Setup
1. Go to Google Cloud Console
2. Enable Gmail API
3. Create credentials (OAuth 2.0)
4. Download JSON to `data/credentials/gmail_credentials.json`
5. Update `.env` with the path

### QQ Mail Quick Setup  
1. Enable IMAP in QQ Mail settings
2. Generate app password
3. Add to `.env`:
```env
QQ_EMAIL=your-email@qq.com
QQ_APP_PASSWORD=your-app-password
```

## 🧪 Testing Your Setup

```bash
# Check everything is working
make check-health

# Run tests
make test

# Try a simple conversation
python main.py terminal --type personal
```

Then ask your bot: "What can you help me with?"

## 🆘 Common Issues

**"Ollama connection failed"**
```bash
# Check if Ollama is running
ollama list

# Start Ollama manually if needed
ollama serve
```

**"DeepSeek model not found"**
```bash
# Download the model
ollama pull deepseek
```

**"Permission denied on data folder"**
```bash
# Fix permissions
chmod -R 755 data/
```

**"Python module not found"**
```bash
# Reinstall dependencies
make install
```

## 📱 Quick Start Checklist

- [ ] Clone repository
- [ ] Install dependencies (`make install`)
- [ ] Install Ollama and DeepSeek (`make ollama-setup`)
- [ ] Run setup wizard (`make setup`)
- [ ] Customize persona files (`data/personal/bio.txt`, etc.)
- [ ] Test the system (`make check-health`)
- [ ] Start your assistant (`make start`)
- [ ] Try sample conversations

## 🎯 Next Steps

Once your basic setup is working:

1. **Add Your Data**: Index your documents and emails
2. **Customize Personality**: Fine-tune your AI's tone and knowledge
3. **Set Up Tools**: Configure email and other integrations
4. **Explore Features**: Try the web interface and advanced commands
5. **Read Full Docs**: Check out the complete README.md

## 🚨 Important Security Notes

- Personal bot runs on `localhost:5000` (private access only)
- Public bot runs on `localhost:5001` (can be exposed if needed)
- Never expose your personal bot to the internet
- Keep your `.env` file secure and never commit it to git
- Regularly backup your data with `make backup-data`

---

**Need help?** Check the full documentation in README.md or create an issue on GitHub. 