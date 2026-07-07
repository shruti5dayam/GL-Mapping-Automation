# GL Mapping Automation

## Overview

GL Mapping Automation is a Python-based financial automation system designed to transform raw bank transactions into structured accounting reports through configurable business rules.

The project automates one of the most repetitive accounting tasks—mapping bank transactions to General Ledger (GL) accounts—and generates financial statements with minimal manual intervention.

The system is designed with a modular ETL architecture, making it easy to extend, maintain, and integrate with future AI-driven financial automation workflows.

---

# Project Goal

The primary objective of this project is to automate the accounting workflow from raw bank statement data to financial reporting.

Instead of manually reviewing thousands of transactions, the system:

- Imports bank statements
- Applies configurable business rules
- Maps transactions to General Ledger accounts
- Enriches transactions using a Chart of Accounts (COA)
- Performs validation and audit checks
- Generates Trial Balance
- Generates Profit & Loss Statement
- Displays results through an interactive Streamlit dashboard

---

# System Workflow

```text
Bank Statements
        │
        ▼
Importer
        │
        ▼
Rule Parser
        │
        ▼
Rule Engine
        │
        ▼
GL Mapping
        │
        ▼
Chart of Accounts Lookup
        │
        ▼
Validation & Audit
        │
        ▼
Trial Balance
        │
        ▼
Profit & Loss Statement
        │
        ▼
Streamlit Dashboard
```

---

# Project Architecture

The project follows a modular pipeline where each component has a single responsibility.

### Importer
Responsible for:

- Reading Excel and CSV files
- Data cleaning
- Schema validation
- Combining multiple bank statements
- Preparing transactions for processing

---

### Rule Parser

Converts configurable rule definitions into executable Python objects.

Responsibilities:

- Parse rule conditions
- Parse rule outputs
- Extract transaction direction
- Build searchable keywords
- Preserve AND / OR rule logic

---

### Rule Engine

The core decision-making engine.

Responsibilities:

- Evaluate every transaction
- Match transactions against business rules
- Score candidate rules
- Select the best matching GL account
- Calculate confidence scores
- Generate mapping audit information

---

### Chart of Accounts Lookup

Enriches mapped transactions with accounting metadata.

Responsibilities:

- Account Number
- Account Type
- Detail Type
- Account Group

---

### Validation Layer

Performs quality checks before financial reporting.

Examples:

- Unmatched transactions
- Missing COA mappings
- Invalid amounts
- Low confidence mappings
- Multiple candidate rules
- Rule usage statistics
- Account usage statistics

---

### Trial Balance Generator

Aggregates mapped transactions into Trial Balance format by:

- Account Number
- Account Name
- Account Type
- Detail Type

---

### Profit & Loss Generator

Builds a structured Profit & Loss statement from the Trial Balance.

Calculates:

- Total Income
- Cost of Goods Sold
- Gross Profit
- Total Expenses
- Net Operating Income
- Net Income

---

### Streamlit Dashboard

Interactive interface providing:

- Transaction summary
- Mapping statistics
- Trial Balance
- Profit & Loss
- Validation reports
- Mapping audit review
- Rule usage analysis
- Account usage analysis

---

# Technologies Used

## Programming

- Python

## Data Processing

- Pandas

## Dashboard

- Streamlit

## Data Sources

- Excel
- CSV

## Financial Concepts

- General Ledger (GL)
- Chart of Accounts (COA)
- Trial Balance
- Profit & Loss Statement

---

# Current Features

- Multiple bank statement support
- Rule-based GL Mapping
- Configurable business rules
- Confidence scoring
- COA enrichment
- Validation framework
- Trial Balance generation
- Profit & Loss generation
- Interactive dashboard
- Downloadable reports

---

# Future Roadmap

This project is being expanded into a complete AI-powered accounting automation platform.

## Phase 1

- Enhanced validation
- Improved dashboard
- Better reporting
- Configurable rule management

---

## Phase 2

- AI-assisted GL Mapping
- Rule recommendation engine
- Confidence-based human review workflow
- Automatic rule conflict detection

---

## Phase 3

- Neo4j Knowledge Graph integration
- Relationship-based financial analysis
- Graph-powered transaction exploration

---

## Phase 4

- LLM-powered Financial Assistant

Capabilities:

- Natural language financial queries
- AI-generated Trial Balance explanations
- AI-generated Profit & Loss insights
- Transaction anomaly explanations
- Intelligent audit assistance

---

## Phase 5

Production Deployment

- FastAPI backend
- REST APIs
- Database integration
- Authentication
- Docker deployment
- Cloud deployment (Azure / AWS)

---

# Project Philosophy

This project is designed with modularity, maintainability, and scalability in mind.

Each processing stage is independent, allowing future components such as AI models, graph databases, and cloud services to be integrated without major architectural changes.

---

# License

# License

This project is licensed under QuadricIT Technologies.