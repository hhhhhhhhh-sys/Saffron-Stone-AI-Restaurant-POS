# 🍽️ Saffron & Stone – AI-Powered Restaurant POS

An AI-powered Restaurant Management and Point of Sale (POS) system built using **React, FastAPI, and MySQL**. The platform simplifies restaurant operations through digital order management, inventory tracking, sales analytics, profit monitoring, and AI-powered business insights using the **Model Context Protocol (MCP)**.

## 🚀 Key Features

### 1. Restaurant Management

- Manage restaurant menus, food items, and pricing.
- Create and manage customer orders.
- Support dine-in ordering through secure QR codes.
- Track order progress in real time.
- Manage customer order history and cancellations.

### 2. Role-Based Access

- **Admin:** Manage menus, employees, inventory, reports, and business analytics.
- **Reception:** Create orders, manage billing, and monitor kitchen progress.
- **Kitchen:** View incoming orders and update preparation status.

### 3. Inventory Management

- Manage ingredients and available stock.
- Configure low-stock alerts and expiry tracking.
- Record restocking and waste adjustments.
- Connect menu items with ingredient recipes.
- Automatically update inventory when applicable orders are placed.

### 4. Sales & Business Analytics

- Monitor daily sales and revenue.
- Analyse orders and cancelled transactions.
- Identify popular food items and product trends.
- Track gross profit and operating expenses.
- Filter analytics using custom date ranges.
- Export business reports as CSV files.

### 5. AI-Powered Admin Chatbot

Integrated with the **Model Context Protocol (MCP)** to help administrators understand restaurant business data.

The AI assistant can help with:

- Sales and revenue analysis.
- Profit and order analysis.
- Cancelled order insights.
- Best-selling and low-performing food items.
- Inventory and stock information.
- Customer analytics.
- Business performance summaries.
- Sales and profit forecasting.

The chatbot uses a dedicated read-only MySQL account to retrieve analytics data. It is accessible only to authenticated administrators.

### 6. Sales Forecasting

- Estimate future sales and revenue.
- Analyse historical sales trends.
- Consider weekday and weekend patterns.
- Account for seasonal and Indian festival-related sales patterns.
- Estimate future expenses and net profit when sufficient data is available.

*Forecasts are estimates based on available historical data, not guaranteed results.*

---

## 🛠️ Technology Stack

| Component         | Technology                   |
| ----------------- | ---------------------------- |
| Frontend          | React, JavaScript, CSS       |
| Backend           | Python, FastAPI              |
| Database          | MySQL 8.0                    |
| AI Integration    | MCP (Model Context Protocol) |
| AI Provider       | OpenAI-compatible API        |
| API Communication | REST API                     |
| Real-Time Updates | WebSockets                   |
| Data Analytics    | Python                       |

---

## 🏗️ Project Architecture

```text
                 ADMIN
                   |
                   v
          React Frontend
                   |
                   v
            FastAPI Backend
                   |
          -------------------
          |                 |
          v                 v
       MySQL DB        Admin AI Chat
                            |
                            v
                       MCP Client
                            |
                            v
                       MCP Server
                            |
                            v
                 Read-Only MySQL User
                            |
                            v
                    Restaurant Data
                            |
                            v
                     AI Provider
                            |
                            v
                  Business Insights
```

---

## 📂 Project Structure

```text
Saffron-Stone-AI-Restaurant-POS/
│
├── backend/
│   ├── app.py
│   ├── admin_analytics.py
│   ├── local_analytics.py
│   ├── admin_chat.py
│   └── mcp_server.py
│
├── database/
│   ├── schema.sql
│   └── migrations/
│       └── 001_smart_platform.sql
│
├── src/
│   ├── AdminChat.jsx
│   └── styles.css
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## ⚙️ Installation & Setup

### Prerequisites

Make sure you have installed:

- Python 3.10 or later
- Node.js and npm
- MySQL 8.0
- Git

### Step 1: Clone the Repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
```

```bash
cd Saffron-Stone-AI-Restaurant-POS
```

### Step 2: Set Up the Database

Create a MySQL database named:

```sql
CREATE DATABASE restaurant_db;
```

For a new installation, execute:

```text
database/schema.sql
```

For an existing installation, back up your database and run the migration once:

```text
database/migrations/001_smart_platform.sql
```

### Step 3: Configure Environment Variables

Copy `.env.example` to `.env` and configure your database and AI settings.

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=restaurant_db
MYSQL_USER=root
MYSQL_PASSWORD=YOUR_DATABASE_PASSWORD

MYSQL_READONLY_USER=restaurant_mcp_reader
MYSQL_READONLY_PASSWORD=YOUR_READONLY_PASSWORD

MCP_SHARED_TOKEN=YOUR_RANDOM_SECRET_TOKEN
MCP_SERVER_URL=http://127.0.0.1:8003/mcp
MCP_PORT=8003

AI_API_URL=https://api.openai.com/v1/chat/completions
AI_API_KEY=YOUR_AI_API_KEY
AI_MODEL=gpt-4o-mini
```

**Important:** Replace all placeholder values with your own configuration. Never upload your `.env` file or expose API keys and database passwords publicly.

### Step 4: Create the Read-Only MySQL Account

Run the following SQL commands in MySQL:

```sql
CREATE USER IF NOT EXISTS
'restaurant_mcp_reader'@'localhost'
IDENTIFIED BY 'YOUR_UNIQUE_PASSWORD';

GRANT SELECT ON restaurant_db.*
TO 'restaurant_mcp_reader'@'localhost';
```

Use the same password in `MYSQL_READONLY_PASSWORD` inside your `.env` file.

### Step 5: Install Backend Dependencies

```bash
python -m pip install -r requirements.txt
```

### Step 6: Start the MCP Server

Open a terminal and run:

```bash
python -m backend.mcp_server
```

The MCP server runs locally on port `8003`.

### Step 7: Start the FastAPI Backend

Open another terminal:

```bash
python -m uvicorn backend.app:app --reload --port 8002
```

Backend API:

```text
http://127.0.0.1:8002
```

API documentation:

```text
http://127.0.0.1:8002/docs
```

### Step 8: Start the React Frontend

Open another terminal:

```bash
npm install
```

```bash
npm run dev
```

Open the application:

```text
http://localhost:5173
```

Log in using your configured administrator account to access the admin dashboard and AI assistant.

---

## 🔐 Security

- Role-based authentication and authorization.
- Dedicated read-only MySQL account for MCP analytics.
- Bearer-token protection for the MCP server.
- Admin-only access to the AI chatbot.
- Environment variables for sensitive credentials.
- MCP server restricted to local access by default.

**Never expose the MCP server directly to the public internet.** Configure HTTPS and appropriate security controls before deploying the application.

---

## 📊 Important Notes

- Forecast accuracy depends on the availability and quality of historical sales data.
- Profit calculations require item cost and expense records.
- Unpaid and cancelled orders are excluded from paid sales analytics.
- Demo/sample orders may be included in reports and forecasts during testing.
- Employee attendance analytics are not currently available because the existing database schema does not contain an employee attendance table.
- The local analytics engine provides a fallback for supported analytics when the external AI provider is unavailable or its quota is exhausted.

---

## 🧪 Run Tests

Execute the backend test suite:

```bash
python -m pytest backend/test_app.py backend/test_admin_chat.py
```

---

## 🔮 Future Enhancements

- Advanced AI-driven business recommendations.
- Improved demand and inventory forecasting.
- More detailed customer behaviour analytics.
- Enhanced restaurant performance dashboards.
- Cloud deployment and production monitoring.

---

## 👨‍💻 Author

**Harsh Singh**

B.Tech – Artificial Intelligence and Data Science

C. V. Raman Global University

---

## 📄 License

This project is developed for educational and demonstration purposes.
