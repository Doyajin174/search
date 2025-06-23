# PPLX AI Search Service

## Overview

This is a Flask-based web application that provides an AI-powered search interface using the Perplexity AI API. The application features a chat-like interface where users can interact with an AI assistant for various types of searches including general queries, news, and academic content. The system includes user personalization, theme switching (light/dark), and session-based conversation history.

## System Architecture

### Frontend Architecture
- **Technology**: Vanilla JavaScript with Bootstrap 5 for responsive UI
- **Structure**: Two-state single-page application (Welcome Screen + Chat Interface)
- **Components**: 
  - Welcome Screen with centered search and model selection
  - Chat Interface with sidebar history and message bubbles
  - Header navigation with logo/home button and theme toggle
  - Suggestion cards and search mode options
  - Responsive design for mobile and desktop

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **API Integration**: Perplexity AI API for chat completions
- **Session Management**: Flask sessions for storing conversation history
- **Deployment**: Gunicorn WSGI server with autoscale deployment target

### Key Design Decisions
- **Two-State UI Architecture**: Welcome Screen for initial interaction, Chat Interface for ongoing conversations
- **Modern AI UX Patterns**: Following ChatGPT/Claude design principles for familiar user experience
- **Database-Driven Architecture**: PostgreSQL for persistent storage of users, conversations, and messages
- **Intelligent Question Classification**: Automatic categorization of user queries (greeting, realtime, learning, info_search, general) for optimized responses
- **Multi-Model AI Support**: Users can select from multiple Perplexity AI models optimized for different tasks
- **State-Based Navigation**: Seamless transitions between welcome and chat modes with proper state management
- **External AI Service**: Integrated Perplexity AI instead of building custom AI models for faster time-to-market
- **Comprehensive Search History System**: Perplexity Library-style conversation management with search, favorites, and date grouping
- **Performance-Optimized**: Virtual scrolling, debounced search, and lazy loading for handling large conversation histories
- **Mobile-First Design**: Responsive sidebar that transforms into overlay on mobile devices

## Key Components

### Backend Components (`app.py`)
- **Main Route (`/`)**: Serves the main chat interface
- **Chat API (`/api/chat`)**: Handles communication with Perplexity AI with intelligent question classification
- **Model Management**: Dynamic AI model selection and recommendation system
- **Source Filtering (`source_filter.py`)**: Advanced relevance verification and quality filtering for search results
- **Conversation CRUD**: Full conversation history management with database persistence
- **User Settings**: Persistent user preferences including preferred AI model
- **Error Handling**: Comprehensive error handling for API failures and validation

### Frontend Components
- **PPLXChatApp Class (`static/script.js`)**: Main application controller managing:
  - Chat functionality and message handling
  - User settings and preferences
  - AI model selection and recommendation
  - Conversation history management
  - Theme management
  - Local storage for persistence
- **Responsive UI (`templates/index.html`)**: Bootstrap-based interface with sidebar navigation and model selection
- **Custom Styling (`static/style.css`)**: CSS variables for theme switching, question type badges, and modern UI design

### Configuration
- **Environment Variables**: API keys and session secrets
- **Deployment Config**: Gunicorn with auto-scaling and port binding
- **Dependencies**: Managed via pyproject.toml with uv lock file

## Data Flow

1. **User Interaction**: User types message in chat interface
2. **Client Processing**: JavaScript captures input, validates, and sends to backend
3. **Session Retrieval**: Flask retrieves conversation history from session
4. **API Integration**: Backend constructs request for Perplexity AI API
5. **AI Processing**: Perplexity AI processes query with context and search scope
6. **Response Handling**: Backend receives AI response and updates session
7. **Client Update**: Frontend receives response and updates chat interface
8. **State Persistence**: Conversation history stored in session and local storage

## External Dependencies

### Core Dependencies
- **Flask**: Web framework and routing
- **Requests**: HTTP client for API communication
- **Gunicorn**: Production WSGI server

### Frontend Libraries
- **Bootstrap 5**: Responsive UI framework
- **Font Awesome**: Icon library
- **Vanilla JavaScript**: No additional JS frameworks

### External Services
- **Perplexity AI API**: Core AI functionality for search and chat
- **Environment Configuration**: API keys and secrets management

### Database Architecture
- **Database**: PostgreSQL with Flask-SQLAlchemy ORM
- **Tables**: 
  - `users` - User profiles and settings
  - `conversations` - Chat sessions with metadata
  - `messages` - Individual chat messages with question type classification
  - `user_sessions` - Session management for user state
- **Features**: 
  - Persistent conversation history
  - Question type classification storage
  - User preference persistence
  - Conversation management (create, read, delete)

## Deployment Strategy

### Production Setup
- **Server**: Gunicorn with multiple workers
- **Scaling**: Autoscale deployment target for handling variable loads
- **Port Configuration**: Configured for port 5000 with reuse-port option
- **Environment**: Nix-based environment with Python 3.11

### Development Workflow
- **Hot Reload**: Gunicorn configured with --reload for development
- **Environment**: Replit-based development with workflow automation
- **Dependencies**: UV package manager for fast dependency resolution

### Infrastructure Requirements
- **Runtime**: Python 3.11 with SSL support
- **Database**: PostgreSQL ready (currently unused)
- **Environment Variables**: Secure API key and session management

## Changelog

```
Changelog:
- June 22, 2025. Initial setup with Flask backend and Perplexity AI integration
- June 22, 2025. Added intelligent question classification system (greeting, realtime, learning, info_search, general)
- June 22, 2025. Integrated PostgreSQL database for persistent storage of users, conversations, and messages
- June 22, 2025. Added conversation history management with CRUD operations
- June 22, 2025. Implemented multi-model AI selection feature with 7 specialized Perplexity models
- June 22, 2025. Added model recommendation system based on question type and content analysis
- June 22, 2025. Implemented sophisticated source filtering and relevance verification system
- June 22, 2025. Redesigned UI with modern AI interface similar to ChatGPT/Claude with clean layout and improved UX
- June 22, 2025. Implemented two-state UI system: Welcome Screen (initial landing) and Chat Interface (conversation mode)
- June 23, 2025. Successfully migrated project from Replit Agent to standard Replit environment
- June 23, 2025. Configured PostgreSQL database connection and environment variables
- June 23, 2025. Removed suggestion cards from welcome screen for cleaner interface
```

## User Preferences

```
Preferred communication style: Simple, everyday language.
UI Preference: Modern AI interface similar to ChatGPT/Claude with clean, professional design.
```