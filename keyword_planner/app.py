import streamlit as st
from scrapper import AppStoreScraper
from aikeyword import AIKeywordGenerator
from typing import cast
from typesense_client import TypesenseClient


st.set_page_config(page_title="Keyword Planner", page_icon="🛰️", layout="wide")

st.title("Welcome to the Keyword Planner Application")

country_options = {
    "us":"United States", 
    "in":"India",
    "ar": "Saudi Arabia",
    "au": "Australia"
}

country_code = st.selectbox(
    "Country Selection",
    options=list(country_options.keys()),
    format_func=lambda code: country_options[code]
)
app_url = st.text_input("App URL", placeholder="Enter Your App URL")

if st.button("Generating AI Keywords"):
    if app_url:
        dbObj = TypesenseClient()
        with st.spinner("Checking for existing data..."):
            existing_details, existing_keywords = dbObj.get_existing_app_data(app_url, str(country_code))

        if existing_details and existing_keywords:
            #st.success("Found existing data in the database!")
            st.subheader("App Details")
            st.json(existing_details)
            st.subheader("AI Generated Keywords")
            st.json(existing_keywords)
        else:
            #st.info("No existing data found. Starting fresh analysis...")
            app_details = None  # Initialize app_details to None
            with st.spinner("Analyzing... wait for a moment!"):
                scraper = AppStoreScraper(app_url, str(country_code))
                app_details = scraper.scrape()

            if app_details:
                ai_generator = AIKeywordGenerator()
                with st.spinner("Generating keywords with AI..."):
                    ai_response = ai_generator.generateKeywords(app_details=app_details)
                
                if ai_response:
                    st.subheader("AI Generated Keywords:")
                    st.json(ai_response)

                    # Prepare the document for ingestion, adhering to SRP
                    doc_to_ingest = dict(app_details)
                    if 'competitor_apps' in doc_to_ingest and isinstance(doc_to_ingest['competitor_apps'], list):
                        doc_to_ingest['competitor_apps'] = [
                            f"{comp['appname']} ({comp['appurl']})" for comp in cast(list, doc_to_ingest['competitor_apps'])
                        ]
                    
                    # Remove keys that are not part of the appDetails schema
                    doc_to_ingest.pop('keywords', None)
                    doc_to_ingest.pop('competitor_apps_keywords', None)

                    # Ingest data into Typesense only on success
                    success, app_details_uid_or_error = dbObj.ingestAppDetails(doc_to_ingest, country=str(country_code))
                    if success:
                        # Extract appid from the original details for ingestAIKeywords
                        app_id = app_details.get("appid", "unknown_id")
                        if app_id == "unknown_id": # Ensure app_id was found/created
                            st.error("Could not determine appid, cannot ingest keywords.")

                        # Pass the returned uid from appDetails ingestion as the app_uid for the keywords document
                        dbObj.ingestAIKeywords(ai_response, 
                                               original_app_details=app_details,
                                               app_details_uid=app_details_uid_or_error,
                                               app_id=app_id, country=str(country_code))
                        st.success("Successfully scraped, generated, and ingested new data!")
                    else:
                        st.error(f"Failed to ingest app details into database: {app_details_uid_or_error}")
                else:
                    st.error("Failed to generate or parse AI keywords. Please check the logs.")
            else:
                st.error("Failed to scrape app details. Please check the URL and try again.")
    else:
        st.warning("Please enter an App URL to start the analysis.")
