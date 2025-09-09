# AI Expense Auditor - Setup Guide

This guide will help you set up and run the AI Expense Auditor system on your local machine.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11+** - [Download Python](https://www.python.org/downloads/)
- **Node.js 18+** - [Download Node.js](https://nodejs.org/)
- **PostgreSQL 15+** - [Download PostgreSQL](https://www.postgresql.org/download/)
- **Redis** - [Download Redis](https://redis.io/download)
- **Git** - [Download Git](https://git-scm.com/downloads)

### Optional (for Docker setup):
- **Docker** - [Download Docker](https://www.docker.com/get-started)
- **Docker Compose** - Usually included with Docker Desktop

## Quick Start (Docker - Recommended)

The easiest way to get started is using Docker Compose:

### 1. Clone and Navigate
```bash
cd "c:\Users\bysan\Downloads\hacktathon\-AI-Expense-Auditor"
```

### 2. Start Services
```bash
docker-compose up -d
```

### 3. Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:5000/api/v1
- **Login**: admin / admin123

### 4. Stop Services
```bash
docker-compose down
```

## Manual Setup

If you prefer to run the services manually:

### Backend Setup

#### 1. Install Python Dependencies
```bash
cd "c:\Users\bysan\Downloads\hacktathon\-AI-Expense-Auditor"
pip install -r requirements.txt
```

#### 2. Install System Dependencies

**Windows:**
```bash
# Install Tesseract OCR
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
# Add to PATH: C:\Program Files\Tesseract-OCR

# Install spaCy model
python -m spacy download en_core_web_sm
```

**macOS:**
```bash
brew install tesseract
python -m spacy download en_core_web_sm
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-eng
python -m spacy download en_core_web_sm
```

#### 3. Database Setup

**Start PostgreSQL:**
```bash
# Create database
createdb expense_auditor

# Or using psql:
psql -U postgres
CREATE DATABASE expense_auditor;
CREATE USER auditor_user WITH PASSWORD 'auditor_pass';
GRANT ALL PRIVILEGES ON DATABASE expense_auditor TO auditor_user;
\q
```

**Start Redis:**
```bash
redis-server
```

#### 4. Environment Configuration
```bash
# Copy environment template
cp env.example .env

# Edit .env file with your settings:
# - DATABASE_URL=postgresql://auditor_user:auditor_pass@localhost:5432/expense_auditor
# - REDIS_URL=redis://localhost:6379/0
# - SECRET_KEY=your-secret-key-here
# - JWT_SECRET_KEY=your-jwt-secret-here
```

#### 5. Initialize Database
```bash
cd backend
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

#### 6. Start Backend Server
```bash
python app.py
```

The backend will be available at: http://localhost:5000

### Frontend Setup

#### 1. Install Dependencies
```bash
cd frontend
npm install
```

#### 2. Start Development Server
```bash
npm start
```

The frontend will be available at: http://localhost:3000

## Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-secret-key-here
FLASK_PORT=5000

# Database Configuration
DATABASE_URL=postgresql://auditor_user:auditor_pass@localhost:5432/expense_auditor
SQLALCHEMY_DATABASE_URI=postgresql://auditor_user:auditor_pass@localhost:5432/expense_auditor
SQLALCHEMY_TRACK_MODIFICATIONS=False

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# JWT Configuration
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ACCESS_TOKEN_EXPIRES=3600

# File Upload Configuration
MAX_CONTENT_LENGTH=16777216  # 16MB
UPLOAD_FOLDER=uploads
ALLOWED_EXTENSIONS=pdf,jpg,jpeg,png,docx,xlsx,json

# ML Model Configuration
MODEL_PATH=./data/models
MODEL_UPDATE_INTERVAL=3600

# Fraud Detection Thresholds
DUPLICATE_THRESHOLD=0.8
INFLATION_THRESHOLD=1.5
GHOST_VENDOR_THRESHOLD=0.7
SPLIT_BILLING_THRESHOLD=0.9

# OCR Configuration
TESSERACT_CMD=/usr/bin/tesseract
OCR_LANGUAGE=eng

# Email Configuration (for notifications)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# Monitoring
PROMETHEUS_PORT=9090
LOG_LEVEL=INFO
```

### Frontend Configuration

Create a `.env` file in the frontend directory:

```env
REACT_APP_API_URL=http://localhost:5000/api/v1
```

## Usage

### 1. Access the Application
- Open your browser and go to http://localhost:3000
- Login with the default credentials:
  - **Username**: admin
  - **Password**: admin123

### 2. Upload Invoices
- Navigate to the "Upload" page
- Drag and drop invoice files (PDF, JPG, PNG, etc.)
- The system will automatically process and analyze them

### 3. View Results
- Check the "Dashboard" for overview statistics
- Go to "Invoices" to see detailed results
- Use "Analytics" for fraud detection insights

### 4. Sample Data
The system includes sample invoice data in `receipt_2.json` for testing.

## API Documentation

### Authentication
All API endpoints require authentication via JWT tokens.

**Login:**
```bash
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

### Key Endpoints

- `GET /api/v1/health` - Health check
- `POST /api/v1/invoices/` - Upload invoice
- `GET /api/v1/invoices/` - List invoices
- `GET /api/v1/analytics/dashboard` - Dashboard data
- `GET /api/v1/analytics/fraud-analysis` - Fraud analysis

## Troubleshooting

### Common Issues

#### 1. Database Connection Error
```bash
# Check if PostgreSQL is running
pg_ctl status

# Check database exists
psql -U postgres -l | grep expense_auditor
```

#### 2. OCR Not Working
```bash
# Check Tesseract installation
tesseract --version

# Test OCR
tesseract test_image.png output
```

#### 3. Frontend Build Issues
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

#### 4. Port Already in Use
```bash
# Find process using port 5000
netstat -ano | findstr :5000

# Kill process (Windows)
taskkill /PID <PID> /F

# Kill process (macOS/Linux)
kill -9 <PID>
```

### Logs

**Backend logs:**
```bash
# Check application logs
tail -f logs/app.log

# Docker logs
docker-compose logs -f backend
```

**Frontend logs:**
```bash
# Development server logs
npm start

# Docker logs
docker-compose logs -f frontend
```

## Development

### Project Structure
```
-AI-Expense-Auditor/
├── backend/                 # Flask backend
│   ├── api/                # API routes
│   ├── models/             # Database models
│   ├── services/           # Business logic
│   ├── utils/              # Utilities
│   └── app.py              # Main application
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components
│   │   ├── stores/         # State management
│   │   └── api/            # API client
│   └── public/             # Static files
├── data/                   # Data storage
├── uploads/                # File uploads
├── docker-compose.yml      # Docker setup
└── requirements.txt        # Python dependencies
```

### Adding New Features

1. **Backend**: Add new routes in `backend/api/routes.py`
2. **Frontend**: Create components in `frontend/src/components/`
3. **Database**: Add models in `backend/models/`
4. **Services**: Add business logic in `backend/services/`

### Testing

**Backend tests:**
```bash
cd backend
python -m pytest tests/
```

**Frontend tests:**
```bash
cd frontend
npm test
```

## Production Deployment

### Security Considerations

1. **Change default passwords**
2. **Use strong secret keys**
3. **Enable HTTPS**
4. **Configure firewall**
5. **Regular security updates**

### Performance Optimization

1. **Use production WSGI server** (Gunicorn)
2. **Enable Redis caching**
3. **Configure database connection pooling**
4. **Use CDN for static files**
5. **Enable compression**

### Monitoring

1. **Set up logging**
2. **Monitor system resources**
3. **Track API performance**
4. **Set up alerts**

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs
3. Check GitHub issues
4. Contact the development team

## License

This project is licensed under the MIT License - see the LICENSE file for details.
