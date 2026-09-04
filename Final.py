import os
import requests
import gspread

from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate

from google.oauth2.service_account import Credentials

# Playwright
from playwright.sync_api import sync_playwright


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# GROQ LLM
# ============================================================

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY")
)


# ============================================================
# APPLICATION WEBSITE URLS
# ============================================================

WEBSITE_URLS = {

    "Adobe Photoshop x64":
        "https://helpx.adobe.com/photoshop/desktop/whats-new/whats-new-in-adobe-photoshop-on-desktop.html",

    "IgorPavlov_7Zip x64":
        "https://www.7-zip.org/",

    "Mindjet_MindManager 2020 x86":
        "https://www.mindmanager.com/en/support/download-library/",

    "Notepad ++ x64":
        "https://notepad-plus-plus.org/downloads/",

    "Oracle Java 8":
        "https://www.oracle.com/java/technologies/downloads/#java8-windows",

    "Oracle Instant Client x86":
        "https://www.oracle.com/database/technologies/instant-client/microsoft-windows-32-downloads.html",

    "VideoLAN_VLC Media Player x64":
        "https://www.videolan.org/vlc/download-windows.html",

    "Microsoft Visual C++ v14 Redistributable":
        "https://aka.ms/vc14/vc_redist.x64.exe"
}


# ============================================================
# PROMPT
# ============================================================

prompt_template = PromptTemplate(
    input_variables=[
        "application",
        "website_content"
    ],

    template="""
You are an expert software-version detection system.

Your task is to determine the latest stable version of the
application using ONLY the information contained in the
website content provided below.

Application:
{application}

Website content:
{website_content}

Rules:

1. Find the latest stable/publicly released version.
2. Do not use beta, alpha, preview, nightly, development,
   insider, or experimental versions.
3. Prefer an explicit version number associated with the
   application release/download.
4. Ignore old versions mentioned in release history.
5. If multiple versions are present, select the newest
   stable version.
6. Do not guess.
7. If the version cannot be determined from the website,
   return UNKNOWN.

Return ONLY Version:

 Version

Example:

27.0.1

Do not provide explanations.
Do not provide additional text.
"""
)


# ============================================================
# PLAYWRIGHT BROWSER
# ============================================================

def get_content_with_playwright(url):

    print("Starting Playwright browser...")

    try:

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=True
            )

            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/138.0.0.0 Safari/537.36"
                ),
                viewport={
                    "width": 1920,
                    "height": 1080
                }
            )

            print(
                "Opening website with Chromium..."
            )

            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=120000
            )

            # Give JavaScript time to render
            page.wait_for_timeout(5000)

            print(
                "Page loaded successfully with Playwright."
            )

            # Get fully rendered HTML
            html = page.content()

            browser.close()

            return html

    except Exception as e:

        print(
            f"Playwright error: {e}"
        )

        return None


# ============================================================
# FUNCTION TO DOWNLOAD WEBSITE
# ============================================================

def get_website_content(url):

    headers = {
        "User-Agent":
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/138.0.0.0 Safari/537.36"
    }

    # --------------------------------------------------------
    # FIRST TRY: REQUESTS
    # --------------------------------------------------------

    print("Trying requests...")

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=20
        )

        response.raise_for_status()

        print(
            f"Requests successful: HTTP {response.status_code}"
        )

        return response.text

    except Exception as e:

        print(
            f"Requests failed: {e}"
        )

        print(
            "Falling back to Playwright..."
        )


    # --------------------------------------------------------
    # SECOND TRY: PLAYWRIGHT
    # --------------------------------------------------------

    return get_content_with_playwright(
        url
    )


# ============================================================
# FUNCTION TO EXTRACT TEXT FROM HTML
# ============================================================

def extract_text(html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # Remove unnecessary elements

    for element in soup([
        "script",
        "style",
        "noscript",
        "svg"
    ]):

        element.decompose()

    text = soup.get_text(
        separator=" ",
        strip=True
    )

    return text


# ============================================================
# FUNCTION TO FIND VERSION USING LLM
# ============================================================

def find_latest_version(
    application,
    website_content
):

    # Limit content so extremely large websites
    # don't consume the entire context.

    website_content = website_content[:30000]

    final_prompt = prompt_template.format(
        application=application,
        website_content=website_content
    )

    try:

        response = llm.invoke(
            final_prompt
        )

        return response.content.strip()

    except Exception as e:

        print(
            f"LLM error for {application}: {e}"
        )

        return f"{application} - UNKNOWN"


# ============================================================
# GOOGLE SHEETS CONNECTION
# ============================================================

scopes = [
    "https://www.googleapis.com/auth/spreadsheets"
]

creds = Credentials.from_service_account_file(
    "gcredentials.json",
    scopes=scopes
)

client = gspread.authorize(
    creds
)

sheet_id = os.getenv(
    "GOOGLE_SHEETS_ID"
)

sheet = client.open_by_key(
    sheet_id
)

worksheet = sheet.sheet1


# ============================================================
# CURRENT TIME
# ============================================================

current_time = datetime.now().strftime(
    "%Y-%m-%d %H:%M:%S"
)


# ============================================================
# PROCESS EVERY APPLICATION
# ============================================================

worksheet.append_row([
    datetime.now().strftime("%A, %d-%m-%Y")
])

row_number = len(worksheet.get_all_values())

worksheet.format(
    f"A{row_number}:D{row_number}",
    {
        "backgroundColor": {
            "red": 0.8,
            "green": 0.8,
            "blue": 0.8
        },
        "textFormat": {
            "bold": True
        }
    }
)

for application, url in WEBSITE_URLS.items():

    print("\n" + "=" * 70)

    print(
        f"Checking: {application}"
    )

    print(
        f"Website: {url}"
    )

    print("=" * 70)


    # --------------------------------------------------------
    # Check whether URL was provided
    # --------------------------------------------------------

    if (
        not url
        or url.startswith("PASTE_")
    ):

        print(
            "URL not provided."
        )

        result = (
            f"{application} - UNKNOWN"
        )

        worksheet.append_row([
            application,
            result,
            url,
            current_time
        ])

        continue


    # --------------------------------------------------------
    # Download website
    # --------------------------------------------------------

    html = get_website_content(
        url
    )


    if html is None:

        print(
            "Could not retrieve website."
        )

        result = (
            f"{application} - UNKNOWN"
        )

        worksheet.append_row([
            application,
            result,
            url,
            current_time
        ])

        continue


    # --------------------------------------------------------
    # Extract readable text
    # --------------------------------------------------------

    website_text = extract_text(
        html
    )


    print(
        f"Extracted {len(website_text)} characters"
    )


    # --------------------------------------------------------
    # Ask LLM to identify latest version
    # --------------------------------------------------------

    result = find_latest_version(
        application,
        website_text
    )


    print(
        f"Result: {result}"
    )


    # --------------------------------------------------------
    # Save to Google Sheets
    # --------------------------------------------------------

    worksheet.append_row([
        application,
        result,
        url,
        current_time
    ])


print("\n========================================")
print("All applications processed successfully.")
print("========================================")