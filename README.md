# QA Status Automation (Excel-Only)

Beginner-friendly project scaffold for generating a QA status HTML report from an Excel workbook.

## Goal

Build an automated utility with this flow:

Excel workbook  
-> Validate Excel data  
-> Calculate QA test metrics  
-> Generate a professional HTML status report  
-> Generate a local preview  
-> Run manually or on a GitHub Actions schedule

## Current Phase

This repository currently contains only **Phase 1 scaffolding**:
- Folder structure
- Environment/config starter files
- Required Python package list
- Sample Excel template

No Python implementation logic has been added yet.

## Project Structure

```text
.
├─ .github/
│  └─ workflows/
├─ output/
├─ src/
│  └─ qa_reporter/
├─ templates/
├─ tests/
├─ .env.example
├─ .gitignore
├─ QA_Status_Template.xlsx
├─ README.md
└─ requirements.txt
```

## Required Python Packages

- pandas
- openpyxl
- Jinja2
- pytest

Install later with:

```bash
pip install -r requirements.txt
```

## Excel Template

Use `QA_Status_Template.xlsx` as the starter workbook.

- Required sheet name: `Daily_Status`
- Required columns:
  - Date
  - Platform
  - Task
  - Status
  - Total
  - Passed
  - Failed
  - Blocked
  - Not Executed
  - Owner
  - Remarks
  - Release
  - UAT Date
  - PROD Date

The workbook contains three clearly marked synthetic sample rows for practice.

## Security and Data Handling

- Excel is the only data source.
- Do not store sensitive production/client data in a public repository.
- Keep real QA workbooks private.
- No real credentials, API keys, or personal client data should be committed.
