# Gemini Budget

Gemini Budget is a modern personal accounting FastAPI backend designed to automate expense tracking using AI. It leverages Google Gemini's multimodal capabilities to extract transaction data from uploaded receipts (PDFs and images) and intelligently matches them with existing records using an agentic reasoning loop.

## 🚀 Features

- **Automated Transaction Extraction**: Upload PDFs or images of receipts, and Gemini will extract the amount, merchant, date, and type.
- **Agentic Transaction Matching**: An intelligent matching system that uses Gemini to reason whether a parsed transaction should create a new record or update an existing one based on historical data.
- **Account Management**: Support for multiple accounts (Cash, Credit Cards, Bank Accounts).
- **Categorization**: Flexible transaction categorization for detailed reporting.
- **Secure Authentication**: Built-in support for identity-aware proxies via `X-Forwarded-Email` headers.
- **Comprehensive Reporting**: Get insights into your spending habits.
- **Robust Testing**: Extensive test suite with high coverage (over 85%).

## 🛠 Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Database**: SQLite with [SQLAlchemy](https://www.sqlalchemy.org/) (Asynchronous)
- **AI Engine**: [Google Gemini (genai)](https://ai.google.dev/)
- **OCR/PDF Processing**: `pdf2image`, `Pillow`
- **Validation**: [Pydantic v2](https://docs.pydantic.dev/)
- **Testing**: `pytest`, `pytest-asyncio`, `pytest-cov`

## 📁 Project Structure

```text
├── backend/
│   ├── routers/       # API endpoints (Accounts, Transactions, etc.)
│   ├── services/      # Business logic (Document Processing, AI Matching)
│   ├── models.py      # SQLAlchemy database models
│   ├── schemas.py     # Pydantic data schemas
│   ├── database.py    # Database connection setup
│   ├── config.py      # App configuration & environment settings
│   ├── tests/         # Unit and integration tests
│   └── main.py        # Application entry point
├── venv/              # Python virtual environment
├── gemini_budget.db   # SQLite database
└── .env               # Environment configuration
```

## ⚙️ Setup & Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd gemini-budget
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   ```

4. **Configure Environment Variables**:
   Create a `.env` file in the root directory:
   ```env
   GOOGLE_GENAI_KEY=your_gemini_api_key_here
   GOOGLE_GENAI_MODEL=gemini-2.0-flash-exp # Or your preferred model
   GENAI_LIMIT_QUERY=5                     # Max agentic queries per transaction
   ```

## 🏃 Running the Application

Start the development server:
```bash
uvicorn backend.main:app --reload
```
The API will be available at `http://127.0.0.1:8000`. You can explore the interactive documentation at `http://127.0.0.1:8000/docs`.

## 🧪 Running Tests

Ensure your virtual environment is active and run:
```bash
PYTHONPATH=. ./venv/bin/pytest backend/tests --cov=backend
```

### 🌍 Running Real-World Tests

To run the real-world tests that use actual image fixtures and the Gemini API:

```bash
GOOGLE_GENAI_KEY=your_api_key_here PYTHONPATH=. ./venv/bin/pytest backend/tests/test_real_fixtures.py -s
```

Note: The `-s` flag allows you to see the output of the extraction results for each fixture.

## 📄 License

This project is licensed under a Proprietary License. See the [LICENSE](LICENSE) file for details.
