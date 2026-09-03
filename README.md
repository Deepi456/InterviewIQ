# InterviewIQ

**AI-Powered Adaptive Career & Interview Coach**

InterviewIQ is a full-stack web application that helps candidates practice for interviews with personalized AI-generated questions, real-time feedback, and adaptive difficulty levels based on their performance.

---

## 🎯 Phase 1 Overview

Phase 1 establishes the complete full-stack foundation with:

- **Backend**: FastAPI with basic health checks and CORS configuration
- **Frontend**: React + Vite with Tailwind CSS and a professional landing page
- **Configuration**: Environment variable management for API keys
- **Project Structure**: Modular architecture ready for future phases

### Phase 1 Features

- ✅ FastAPI backend running on `http://localhost:8000`
- ✅ React frontend running on `http://localhost:5173`
- ✅ Root endpoint: `GET /` (API status)
- ✅ Health check endpoint: `GET /api/health`
- ✅ CORS configured for frontend-backend communication
- ✅ Professional landing page with "Start Interview" button
- ✅ Environment variable configuration system
- ✅ Project structure ready for skill analysis, mock interviews, and reports

### Future Phases

- **Phase 2**: Interview setup (role selection, job description parsing, skill analysis)
- **Phase 3**: Mock interview flow with adaptive AI questions
- **Phase 4**: Performance evaluation and feedback system
- **Phase 5**: n8n automation and email reporting
- **Phase 6**: PDF/DOCX export and advanced analytics

---

## 🛠 Technology Stack

### Backend
- **Framework**: FastAPI
- **Server**: Uvicorn
- **Language**: Python 3.8+
- **Configuration**: python-dotenv
- **Validation**: Pydantic

### Frontend
- **Framework**: React 18+
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **HTTP Client**: Axios

### Future Integrations
- **AI/LLM**: OpenAI API + LangChain (Phase 2+)
- **Database**: SQLite (Phase 2+)
- **Automation**: n8n (Phase 5+)
- **Export**: PDF/DOCX libraries (Phase 6+)

---

## 📁 Project Structure

```
InterviewIQ/
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app instance and routes
│   │   ├── config.py               # Configuration and settings
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── health.py           # Health check endpoint
│   │
│   ├── requirements.txt             # Python dependencies
│   ├── .env.example                 # Example environment variables
│   └── .gitignore                   # Backend-specific gitignore
│
├── frontend/
│   ├── src/
│   │   ├── main.jsx                 # React entry point
│   │   ├── App.jsx                  # Main app component
│   │   ├── App.css                  # App styles
│   │   ├── index.css                # Global styles with Tailwind
│   │   └── pages/
│   │       └── LandingPage.jsx      # Landing page component
│   │
│   ├── index.html                   # HTML entry point
│   ├── package.json                 # Node.js dependencies
│   ├── vite.config.js               # Vite configuration
│   ├── tailwind.config.js           # Tailwind CSS configuration
│   ├── postcss.config.js            # PostCSS configuration
│   ├── .env.example                 # Example environment variables
│   └── .gitignore                   # Frontend-specific gitignore
│
├── data/
│   └── .gitkeep                     # Placeholder for data/question bank
│
├── reports/
│   └── .gitkeep                     # Placeholder for generated reports
│
├── README.md                         # This file
└── .gitignore                        # Root-level gitignore
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.8+** (for backend)
- **Node.js 18+** (for frontend)
- **npm or yarn** (for frontend package management)

### Backend Setup

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment:**
   - **Windows:**
     ```bash
     venv\Scripts\activate
     ```
   - **macOS/Linux:**
     ```bash
     source venv/bin/activate
     ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Create a .env file:**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your API keys (or leave them empty for Phase 1 testing).

6. **Run the backend:**
   ```bash
   python -m app.main
   ```
   
   Or with Uvicorn directly:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   The backend will be available at: **`http://localhost:8000`**

### Frontend Setup

1. **Open a new terminal and navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Create a .env file:**
   ```bash
   cp .env.example .env
   ```

4. **Start the development server:**
   ```bash
   npm run dev
   ```

   The frontend will be available at: **`http://localhost:5173`**

---

## ✅ Testing

### Test Backend Endpoints

1. **Root endpoint:**
   ```bash
   curl http://localhost:8000/
   ```
   
   Expected response:
   ```json
   {
     "message": "InterviewIQ API is running"
   }
   ```

2. **Health check endpoint:**
   ```bash
   curl http://localhost:8000/api/health
   ```
   
   Expected response:
   ```json
   {
     "status": "healthy",
     "service": "InterviewIQ"
   }
   ```

### Test Frontend

1. Open your browser and navigate to `http://localhost:5173`
2. You should see the InterviewIQ landing page
3. The backend status indicator (bottom-right) should show "✓ Backend Connected"
4. Click "Start Interview" to see the setup screen placeholder

---

## 📝 Configuration

### Environment Variables

**Backend** (`backend/.env`):
```
OPENAI_API_KEY=your-api-key-here
N8N_WEBHOOK_URL=your-webhook-url-here
```

**Frontend** (`frontend/.env`):
```
VITE_API_URL=http://localhost:8000
```

For Phase 1, these can be left empty for testing.

---

## 🔗 API Endpoints (Phase 1)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API status message |
| `GET` | `/api/health` | Health check |

### Future Endpoints (Phase 2+)

- `POST /api/interview/setup` - Start interview setup
- `POST /api/interview/analyze-job` - Analyze job description
- `GET /api/interview/questions` - Get adaptive questions
- `POST /api/interview/submit-answer` - Submit interview answer
- `GET /api/interview/feedback` - Get performance feedback
- `GET /api/reports/generate` - Generate performance report

---

## 📦 Dependencies

### Backend (`requirements.txt`)
- `fastapi==0.104.1` - Web framework
- `uvicorn==0.24.0` - ASGI server
- `python-dotenv==1.0.0` - Environment variable management
- `pydantic==2.4.2` - Data validation

### Frontend (`package.json`)
- `react@18.2.0` - UI library
- `react-dom@18.2.0` - React DOM
- `vite@5.0.0` - Build tool
- `tailwindcss@3.3.0` - CSS framework
- `axios@1.6.0` - HTTP client

---

## 🛡️ Security Notes

- **Never commit `.env` files** to version control
- **Use `.env.example`** as a template
- API keys are loaded from environment variables only
- CORS is configured to allow `http://localhost:5173` and `http://localhost:3000` (development)

---

## 🚧 Development Guidelines

### Rules for This Phase
1. ✅ Focus on Phase 1 only
2. ✅ Keep architecture modular for future phases
3. ✅ No authentication yet
4. ✅ No database connections yet (SQLite setup comes in Phase 2)
5. ✅ No LangChain or OpenAI integration yet
6. ✅ No n8n automation yet

### Adding Features Later
- Extend `backend/app/routes/` for new endpoints
- Add new pages under `frontend/src/pages/`
- Update configuration in `app/config.py`
- Manage dependencies in their respective `requirements.txt` or `package.json`

---

## 🐛 Troubleshooting

### Backend won't start
- Ensure Python 3.8+ is installed: `python --version`
- Check that virtual environment is activated
- Verify all dependencies are installed: `pip list | grep fastapi`

### Frontend won't compile
- Ensure Node.js 18+ is installed: `node --version`
- Delete `node_modules/` and `package-lock.json`, then run `npm install` again
- Check that Vite and Tailwind are installed

### Backend connection fails
- Verify backend is running on `http://localhost:8000`
- Check browser console for CORS errors
- Ensure both services are on allowed origins in `app/config.py`

### Port conflicts
- **Backend port 8000 busy?** Change in `app/main.py` and update frontend proxy
- **Frontend port 5173 busy?** Vite will auto-increment to 5174, etc.

---

## 📚 Next Steps

1. **Phase 2**: Interview setup form, job description parsing, and skill extraction
2. **Phase 3**: Mock interview flow with adaptive questions
3. **Phase 4**: AI-powered evaluation and feedback
4. **Phase 5**: n8n automation and email reporting
5. **Phase 6**: Advanced analytics and export options

---

## 📄 License

InterviewIQ © 2026. All rights reserved.

---

## 💡 Support

For issues or questions about Phase 1, refer to the troubleshooting section above or check the project structure.

Happy interviewing! 🎯
