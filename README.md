Overview

Automated Software Version Checker is a Python automation project designed to monitor software vendors’ websites and identify the latest stable versions of applications.

Instead of manually checking multiple vendor websites, the system automatically:

1.  Accesses application release/download websites
2.  Uses requests for normal websites
3.  Falls back to Playwright when browser rendering is required
4.  Extracts readable website content using BeautifulSoup
5.  Uses a Groq-powered LLM to identify the latest stable version
6.  Stores the results in Google Sheets
7.  Runs automatically using GitHub Actions

The project is designed to be useful for software inventory, application management, patch monitoring, and automation workflows.


Website Content
      │
      ▼
BeautifulSoup
      │
      ▼
Extracted Text
      │
      ▼
Groq LLM
      │
      ▼
Application Version


Author
Sanjay R
GitHub: ⁠@Sanjayr4


