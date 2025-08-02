# Invoice Parser with AI-Powered Invoice Processing System 🚀

A comprehensive invoice processing system with AI-powered extraction, product matching, and advanced RAG analytics chat interface.

## 🌟 Features

### 📄 Invoice Upload & Processing
- **AI-Powered Extraction**: Claude AI extracts invoice data with high accuracy
- **Automatic Product Matching**: Fuzzy matching with confidence scoring
- **Price History Tracking**: Complete cost tracking with invoice traceability
- **Vendor Detection**: Automatic vendor identification and processing
- 🔍 **Smart Matching**: Fuzzy matching for vendor and product identification
- 📊 **Data Processing**: Pandas-based data manipulation and analysis
- 🧪 **Comprehensive Testing**: Full test suite for reliability
- 📝 **Structured Logging**: Detailed logging for monitoring and debugging

## Prerequisites

- Python 3.8 or higher
- Supabase account and project
- Anthropic API key for Claude AI

## Setup Instructions

### 1. Check Python Version

```bash
python --version  # Should be 3.8 or higher
```

If you don't have Python 3.8+, download it from [python.org](https://www.python.org/downloads/)

### 2. Clone and Navigate to Project

```bash
cd invoice-parser-supabase
```

### 3. Create Virtual Environment

```bash
python -m venv venv
```

### 4. Activate Virtual Environment

**On Windows:**
```bash
venv\Scripts\activate
```

**On Mac/Linux:**
```bash
source venv/bin/activate
```

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

### 6. Configure Environment Variables

1. Copy the `.env` file and update with your credentials:
   ```bash
   cp .env .env.backup  # Backup existing config
   ```

2. Update the `.env` file with your actual credentials:
   - **Supabase URL**: Get from your Supabase dashboard
   - **Supabase Keys**: Anonymous and service keys from Supabase
   - **Anthropic API Key**: Get from your Anthropic account
   - **Database URL**: PostgreSQL connection string from Supabase

### 7. Run Setup Tests

```bash
python -m pytest tests/test_component_1_setup.py -v
```

Expected output: All 5 tests should pass ✅

### 8. Run Main Application

```bash
python main.py
```

This will display the system status and component readiness.

## Project Structure

```
invoice-parser-supabase/
├── api/                    # FastAPI endpoints
├── components/             # Reusable components
├── config/                 # Configuration files
│   ├── settings.py        # Environment settings
│   └── logging_config.py  # Logging configuration
├── database/              # Database models and connections
├── frontend/              # Frontend interface
├── parsers/               # PDF and invoice parsing logic
├── processed/             # Processed invoice files
├── results/               # Processing results
├── scripts/               # Utility scripts
├── services/              # Business logic services
├── tests/                 # Test files
├── uploads/               # Uploaded invoice files
├── logs/                  # Application logs
├── .env                   # Environment variables
├── requirements.txt       # Python dependencies
├── main.py               # Application entry point
└── README.md             # This file
```

## Component Status

- ✅ **Environment Setup** - Complete
- ❌ **Database Configuration** - Pending
- ❌ **PDF Extraction** - Pending
- ❌ **Vendor Detection** - Pending
- ❌ **Product Data Loader** - Pending
- ❌ **Claude AI Processing** - Pending
- ❌ **Product Matching** - Pending
- ❌ **Price Updates** - Pending
- ❌ **Processing Pipeline** - Pending
- ❌ **Advanced RAG System** - Pending

## Development Workflow

1. **Run tests** before making changes:
   ```bash
   pytest -v
   ```

2. **Check system status**:
   ```bash
   python main.py
   ```

3. **View logs** for debugging:
   ```bash
   tail -f logs/application.log
   ```

## Troubleshooting

### Common Issues

1. **Import errors**: Make sure virtual environment is activated
2. **Package conflicts**: Try recreating the virtual environment
3. **Permission errors**: Check file permissions for upload/processed directories
4. **Database connection**: Verify Supabase credentials in `.env`

### Getting Help

- Check the logs in `logs/application.log`
- Run the setup tests to identify configuration issues
- Verify all environment variables are properly set

## Next Steps

1. Set up database models and Supabase client
2. Implement PDF parsing and text extraction
3. Build Claude AI integration for data extraction
4. Create FastAPI endpoints for file upload and processing
5. Develop the frontend interface

## License

This project is for internal use and development.
