#iOS Keyword Generator

1. Introduction: 
This project is an iOS Keyword Generator that leverages a combination of AI models and search technology to suggest relevant keywords for App Store Optimization (ASO). The application is designed to ingest data from an App Store scraping API, process it using a large language model, and perform a vector search to find high-impact keyword suggestions.

2. Tech Stack:
The application is built using a modern and performant tech stack.
Frontend: Streamlit for a simple and fast web interface.
Backend: Python
Core Libraries:LangChain: For orchestrating the various components (LLM, vector search, data parsing).
Groq: A high-speed inference engine for low-latency LLM operations.
Typesense: A fast, open-source search engine used for vector search.
Requests/aiohttp: For making API calls to the data scraping service.
Dependency Management: pip and a requirements.txt file.

3. Prerequisites:
Before you begin, ensure you have the following installed on your local machine:
Python 3.8+
pip (Python package installer)
Virtual environment tool (e.g., venv or conda)

4. Installation:
Follow these steps to set up the project for local development.

Clone the Repository:
`git clone [repository_url]`
`cd [repository_name]`

Create and Activate a Virtual Environment:

It is a best practice to use a virtual environment to manage project dependencies and avoid conflicts with other Python projects on your system.

# Using venv
`python3 -m venv venv`
`source venv/bin/activate`  # On macOS/Linux
`venv\Scripts\activate`     # On Windows

Install Dependencies:
This project uses `pyproject.toml` to manage dependencies. You can use `pip` or a modern, faster tool like `uv` to install them.

# Using pip
`pip install .`

# Using uv (recommended for speed)
`uv pip install .`

5. Configuration for Local Development:
To run the application, you need to configure your API keys for the various services. This project uses a `.env` file for managing environment variables.

Create the `.env` File:
In the root of your project, create a file named `.env`.
`touch .env`

Add Your API Keys:
Open the `.env` file and add your API keys as follows. This file should be added to your `.gitignore` to keep your secrets out of version control.
```
GROQ_API_KEY="your_groq_api_key_here"
TYPESENSE_HOST="your_typesense_host_url"
TYPESENSE_API_KEY="your_typesense_api_key_here"
```
Note: Replace the placeholder values with your actual API keys and host information.

6. Running the Application:
Once the dependencies are installed and the configuration is complete, you can start the Streamlit application.

`streamlit run app.py`

This will start the development server and open the application in your default web browser.

8. TroubleshootingModuleNotFoundError: 

Ensure you have activated your virtual environment and installed the dependencies correctly using `pip install -r requirements.txt`.
KeyError: 'SCRAPER_API_KEY': Double-check that you have created the `.streamlit/secrets.toml` file and populated it with all the required keys exactly as shown in Section 5.

9. Contribution If you would like to contribute, please fork the repository and submit a pull request with your changes.