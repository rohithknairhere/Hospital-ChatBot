# 🏥 Hospital Revenue Leakage & Surgery Audit Dual Chatbot

This is a premium, full-stack analytical web application designed to identify and analyze hospital billing records and surgical discrepancies using an elegant dual-chatbot interface powered by **Google Gemini 2.5 Flash**.

---

## 🌟 Chatbot Core Functions

*   **💰 Revenue Leakage Chatbot:** Focused on identifying missed clinical charges, auditing unbilled procedures, analyzing floor/departmental leakage, and identifying historical leakage trends.
*   **🏥 Surgery Audit Chatbot:** Focused on comparing actual scheduled surgical logs with billed procedures recorded in the Hospital Information System (HIS) to isolate discrepancies and track financial leakage by surgeon and specialty.

---

## 📂 Project Structure

*   [**`CODE_DOCUMENTATION.md`**](file:///c:/Users/Rohith/AntiGravity/RevenueLeakageProject/CODE_DOCUMENTATION.md): A comprehensive technical architectural documentation file detailing functions, algorithms, states, and DB structures.
*   `backend/`: The FastAPI application directory.
    *   [**`backend/main.py`**](file:///c:/Users/Rohith/AntiGravity/RevenueLeakageProject/backend/main.py): The core API server, query aggregator, autocomplete engine, and Gemini connector.
    *   [**`backend/ingest.py`**](file:///c:/Users/Rohith/AntiGravity/RevenueLeakageProject/backend/ingest.py): Automated pipeline to ingest raw hospital Excel sheets and PDFs into SQLite.
    *   [**`backend/requirements.txt`**](file:///c:/Users/Rohith/AntiGravity/RevenueLeakageProject/backend/requirements.txt): Python dependencies.
*   `frontend/`: The React-based user interface.
    *   [**`frontend/index.html`**](file:///c:/Users/Rohith/AntiGravity/RevenueLeakageProject/frontend/index.html): The SPA entry page styled with Tailwinds, Google Fonts, and embedded React.
    *   [**`frontend/app.js`**](file:///c:/Users/Rohith/AntiGravity/RevenueLeakageProject/frontend/app.js): React dashboard, charting logic via Recharts, and autocomplete search bar.
*   `db/`: Local SQLite databases.
*   `data/raw/`: Store raw, unprocessed Excel and PDF data.
*   [**`inline.py`**](file:///c:/Users/Rohith/AntiGravity/RevenueLeakageProject/inline.py): A helper script to compile separate index.html and app.js into a single static file.
*   [**`test_audit.py`**](file:///c:/Users/Rohith/AntiGravity/RevenueLeakageProject/test_audit.py): Verification script to test offline query executions and SQL joins.
*   [**`test_date_extraction.py`**](file:///c:/Users/Rohith/AntiGravity/RevenueLeakageProject/test_date_extraction.py): Verification script to test free-text temporal query extraction.

---

## 🔑 Administrator Credentials

The application uses role-based access control. Log in using one of the following mock administrator credentials:

| Username | Password | Authorized Chatbots |
| :--- | :--- | :--- |
| **`Admin`** | `Admin` | Both chatbots (Revenue Leakage & Surgery Audit) |
| **`Admin1`** | `Admin1` | Revenue Leakage Chatbot only |
| **`Admin2`** | `Admin2` | Surgery Audit Chatbot only |

---

## ⚙️ Quick Start Setup Instructions

### 1. Prerequisites
Ensure you have **Python 3.10+** installed on your operating system.

### 2. Backend Setup
Navigate to the root directory of the project in your terminal and install all Python package dependencies:
```bash
pip install -r backend/requirements.txt
```

### 3. Run the Data Ingestion Pipeline
Before launching the server, populate the database with the hospital's raw audit spreadsheets:
```bash
python backend/ingest.py
```
*(Note: Parsing multiple large hospital sheets and PDF catalogs might take a few moments.)*

### 4. Start the Backend API Server
Launch the FastAPI server:
```bash
python backend/main.py
```
The REST API server will run locally at: `http://localhost:8000`.

### 5. Access the Frontend Dashboard
Since the React app uses standard CDN-loaded scripts, you can open [**`frontend/index.html`**](file:///c:/Users/Rohith/AntiGravity/RevenueLeakageProject/frontend/index.html) directly in any web browser. Alternatively, serve it locally using Python's built-in HTTP server:
```bash
cd frontend
python -m http.server 3000
```
Then visit `http://localhost:3000` in your web browser.

### 6. (Optional) Compile Single-File Build
To bundle the frontend assets into a single static HTML file for easier sharing, run:
```bash
python inline.py
```
This inlines `app.js` into the `index.html` file automatically.
