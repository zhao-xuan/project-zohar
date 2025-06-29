# Metadata-Based Search Guide

## Overview

The enhanced PersonalDataRetriever now supports advanced metadata-based searches including temporal queries, sender filtering, date-based searches, and conversation analysis. This enables you to find specific information based on when it was sent, who sent it, and other metadata criteria.

## 🔍 Key Features

### 1. **Temporal Queries**
Find messages based on time relationships:
- **Earliest/First/Oldest**: `"earliest text message from Kristiane"`
- **Latest/Last/Newest/Recent**: `"latest message from Kristiane"`
- **Date-specific**: `"messages on 2022-03-13"`

### 2. **Sender-Based Filtering**
Search for messages from specific people:
- `"messages from Kristiane"`
- `"what did Kristiane say about the agreement"`
- `"find all messages sent by Kristiane"`

### 3. **Date and Time Analysis**
- **Specific dates**: `"messages on 3/13/22"`
- **Date ranges**: `"messages between March 2022 and June 2022"`
- **Timeline analysis**: `"conversation timeline with Kristiane"`

### 4. **File and Content Type Filtering**
- **Documents**: `"document files from Kristiane"`
- **Images**: `"image files shared in conversation"`
- **Audio**: `"audio messages from last month"`

## 📊 Search Results Enhancement

### Chat Message Format
```
💬 CHAT MESSAGE:
📅 Date: 2022-05-01 00:22:05
👤 Sender: Kristiane Backer
📝 Content:
I would LOVE to demonstrate to you one day~
```

### Document Format
```
📄 LODGER AGREEMENT DOCUMENT: filename.doc
This is a lodger/rental agreement document shared via WhatsApp.
File type: .doc
Status: Available for review
```

## 🛠️ Available Methods

### Core Retrieval Methods

```python
# General enhanced search (automatically detects query type)
await retriever.retrieve_relevant_data("earliest messages from Kristiane", limit=5)

# Specialized temporal methods
await retriever.get_earliest_messages("Kristiane", limit=5)
await retriever.get_latest_messages("Kristiane", limit=5)

# Date-based searches
await retriever.get_messages_by_date("2022-03-13", limit=10)
await retriever.search_by_date_range("2022-03-01", "2022-03-31", limit=20)

# Sender-based searches
await retriever.search_by_sender("Kristiane", limit=10)

# Timeline analysis
await retriever.analyze_conversation_timeline("Kristiane")
```

### Timeline Analysis Output
```python
{
    "total_messages": 25,
    "date_range": {
        "earliest": "2021-06-30 14:26:51",
        "latest": "2025-01-12 09:05:14"
    },
    "daily_counts": {
        "2022-10-21": 2,
        "2025-01-12": 2,
        "2024-06-24": 2
    },
    "most_active_days": [
        ("2022-10-21", 2),
        ("2025-01-12", 2),
        ("2024-06-24", 2)
    ]
}
```

## 🎯 Example Queries

### Finding Earliest Messages
- `"What was the earliest text message from Kristiane?"`
- `"Show me the first message in our conversation"`
- `"Find the oldest message from Kristiane Backer"`

### Finding Latest Messages
- `"What was the latest message from Kristiane?"`
- `"Show me the most recent messages from Kristiane"`
- `"What did Kristiane say most recently?"`

### Date-Specific Searches
- `"What messages were sent on March 13, 2022?"`
- `"Show me all messages from 2022-03-13"`
- `"Find messages sent on 3/13/22"`

### Sender Analysis
- `"How many messages did Kristiane send?"`
- `"Show me Kristiane's conversation timeline"`
- `"What were the most active days for messages from Kristiane?"`

### Content + Metadata Combinations
- `"Find the lodger agreement document from Kristiane"`
- `"Show me the earliest message about the rental agreement"`
- `"What documents did Kristiane share in March 2022?"`

## 🔧 Technical Implementation

### Date Parsing
- **WhatsApp Format**: `[3/13/22, 10:11:07 PM]`
- **ISO Format**: `2022-03-13T22:11:07`
- **Handles**: 2-digit and 4-digit years, 12-hour and 24-hour time

### Sender Extraction
- **Pattern**: `[date] Sender Name: message content`
- **Filters**: System messages and formatting artifacts
- **Supports**: Various chat platforms and formats

### Query Type Detection
Automatically detects:
- **Temporal**: earliest, latest, first, last, oldest, newest
- **Sender**: from, by, sent by, messages from
- **Date**: on, in 20XX, specific dates
- **Timeline**: timeline, conversation history, over time

### Metadata Filtering
- **File Types**: .pdf, .doc, .docx, .jpg, .mp3, etc.
- **Content Types**: documents, images, audio, video
- **Temporal**: chronological sorting and filtering
- **Relevance**: combines semantic similarity with metadata criteria

## 📝 Usage in Chat Interface

When chatting with the personal agent, you can now use natural language queries like:

```
"What was the earliest message from Kristiane?"
"Show me the lodger's agreement we discussed"
"Find all messages from March 2022"
"What was our conversation timeline like?"
"Show me the latest document Kristiane shared"
```

The agent will automatically:
1. Detect the query type (temporal, sender-based, etc.)
2. Apply appropriate filtering and sorting
3. Format results with dates, senders, and metadata
4. Provide chronological context and file locations

## 🎉 Benefits

- **Precision**: Find exact messages by date, time, and sender
- **Context**: Get temporal context with every result
- **Organization**: Results sorted chronologically when appropriate
- **Metadata Rich**: File types, locations, and timestamps included
- **Natural Language**: Use conversational queries instead of complex filters 