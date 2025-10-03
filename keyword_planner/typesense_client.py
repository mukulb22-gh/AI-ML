import typesense
from datetime import datetime
from typing import Any, Dict, cast, Optional, Tuple, TYPE_CHECKING
import uuid
import re
import os
from dotenv import load_dotenv
from scrapper import AppDetails
from aikeyword import AIResponse

load_dotenv()

typesense_host = os.getenv("TYPESENSE_HOST")
if not typesense_host:
    raise ValueError("TYPESENSE_HOST environment variable not set.")

typesense_api_key = os.getenv("TYPESENSE_API_KEY")
if not typesense_api_key:
    raise ValueError("TYPESENSE_API_KEY environment variable not set.")

if TYPE_CHECKING:
    from typesense.api.documents import SearchParameters  # type: ignore

class TypesenseClient:
    
    def __init__(self,api_key: str = typesense_api_key, host: str = typesense_host):

        self.client = typesense.Client({
            'api_key': api_key,
            'nodes': [{
                'host': host,
                'port': 443,
                'protocol': 'https'
            }],
            'connection_timeout_seconds': 2
        })

    def appDetailsSchema(self):
        collection_name = "appDetails"
        schema = {
            "name": collection_name,
            "fields": [
                {"name":"uid", "type": "string"},
                {"name":"appid", "type": "string", "facet": True},
                {"name":"country", "type": "string"},
                {"name":"appurl", "type": "string", "facet": True},
                {"name":"appname", "type": "string", "facet": True},
                {"name":"appsubtitle", "type": "string"},
                {"name":"rating", "type": "string"},
                {"name":"size", "type": "string"},
                {"name":"category", "type": "string", "facet": True},
                {"name":"iphone_screenshots", "type": "string[]"},
                {"name":"description", "type": "string"},
                {"name":"competitor_apps", "type": "string[]"},
                {"name": "ingested_datetime", "type": "string"},
                {"name": "modified_datetime", "type": "string"}
            ]
        }

        try:
            if collection_name in self.client.collections:
                print(f"Collection '{collection_name}' already exists.")
            else:
                self.client.collections.create(schema)
                print(f"Schema of {schema['name']} is created successfully")
        except Exception as e:
            print(f"Error creating collection {collection_name} - ErrorDetails:{e}")

    def aiKeywordsSchema(self) :
        collection_name = "aiKeywords"
        schema = {
            "name": collection_name,
            "fields": [
                {"name":"uid", "type": "string"},
                {"name":"app_uid", "type":"string"},
                {"name":"appid", "type": "string", "facet": True},
                {"name":"country", "type": "string"},
                {"name":"keywords", "type": "string[]"},
                {"name": "competitor_apps", "type": "string[]"},
                {"name": "competitor_apps_keywords", "type": "string[]"},
                {"name":"ai_keywords", "type":"string[]"},
                {"name": "ai_comp_keywords", "type": "string[]"},
                {"name": "ingested_datetime", "type": "string"},
                {"name": "modified_datetime", "type": "string"}
            ]
        }

        try:
            if collection_name in self.client.collections:
                print(f"Schema of {collection_name} already exists.")
            else:
                self.client.collections.create(schema)
                print(f"Schema of {schema['name']} is created successfully")

        except typesense.exceptions.TypesenseAPIException as e:
            print(f"Error creating collection {e}")

    def get_existing_app_data(self, app_url: str, country: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Checks if app data already exists in Typesense and returns it if found.
        Searches for app details, and if found, uses the appid to find the corresponding AI keywords.
        """
        app_details_collection = "appDetails"
        ai_keywords_collection = "aiKeywords"

        # Prepare the URL to match how it's stored in the database
        prepared_app_url = app_url
        if re.search(r"\/[a-z]{2}\/", app_url):
            prepared_app_url = re.sub(r"\/[a-z]{2}\/", f"/{country}/", app_url)
        else:
            prepared_app_url = app_url.replace("apps.apple.com/", f"apps.apple.com/{country}/")

        try:
            # 1. Search for the app in the appDetails collection
            search_params: "SearchParameters" = {
                'q': prepared_app_url,
                'query_by': 'appurl',
                'filter_by': f'country:={country}'
            }
            search_result = self.client.collections[app_details_collection].documents.search(search_params) # type: ignore

            if search_result['found'] > 0 and search_result['hits'][0]['document']['appurl'] == prepared_app_url:
                app_details_doc: Dict[str, Any] = dict(search_result['hits'][0]['document'])
                appid = app_details_doc.get('appid')
                print(f"Found existing app details for appid: {appid}")

                if not appid:
                    return app_details_doc, None # Found details but no appid to link.

                # 2. Search for the corresponding AI keywords
                
                keyword_search_params = {'q': '*', 'filter_by': f'appid:={appid} && country:={country}'}
                keyword_search_result = self.client.collections[ai_keywords_collection].documents.search(keyword_search_params) # type: ignore

                if keyword_search_result['found'] > 0:
                    return app_details_doc, dict(keyword_search_result['hits'][0]['document'])
                return app_details_doc, None  # Return app details even if keywords are missing.
        except Exception as e:
            print(f"Error searching for existing app data: {e}")
        return None, None

    def ingestAppDetails(self, app_details: AppDetails, country: str) -> tuple[bool, str]:
        collection_name = "appDetails"
        # Create a general dictionary from the TypedDict to allow adding new keys for ingestion.
        doc_to_ingest: Dict[str, Any] = dict(app_details)
        appid = doc_to_ingest.get("appid", "unknown_id")

        ingestion_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        doc_to_ingest["uid"] = str(uuid.uuid4())
        doc_to_ingest["ingested_datetime"] = ingestion_date
        doc_to_ingest["modified_datetime"] = ingestion_date
        doc_to_ingest["country"] = country
        
        try:
            self.client.collections[collection_name].documents.import_([doc_to_ingest], {"action": "upsert"}) # type: ignore
            return True, str(doc_to_ingest.get('uid'))
        except Exception as e:
            print(f"Error ingesting app details: {e}")
            return False, f"Error: {e}"


    def ingestAIKeywords(self, ai_response: AIResponse, original_app_details: AppDetails, app_details_uid: str, app_id: str, country: str) -> str:
        collection_name = "aiKeywords"
        ingestion_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            # **FIX**: Build the document from scratch based on the schema
            aikeywords_data = ai_response.get("aikeywords", {"appKeywords": [], "compKeywords": {}})
            comp_keywords_dict = aikeywords_data.get("compKeywords", {})

            # Flatten the competitor keywords dictionary into a list of strings
            ai_comp_keywords_flat = [
                f"{app_name}: {', '.join(keywords)}" for app_name, keywords in comp_keywords_dict.items()
            ]

            document = {
                "uid": str(uuid.uuid4()),
                "app_uid": app_details_uid,
                "appid": app_id,
                "country": country,
                "keywords": original_app_details.get("keywords", []),
                "competitor_apps": [comp["appname"] for comp in original_app_details.get("competitor_apps", [])],
                "competitor_apps_keywords": [f"{comp['appname']}: {', '.join(comp['keywords'])}" for comp in original_app_details.get("competitor_apps_keywords", [])],
                "ai_keywords": aikeywords_data.get("appKeywords", []),
                "ai_comp_keywords": ai_comp_keywords_flat,
                "ingested_datetime": ingestion_date,
                "modified_datetime": ingestion_date,
            }

            self.client.collections[collection_name].documents.import_([document], {"action": "upsert"})
            return "Success"
        except Exception as e:
            print(f"Error ingesting AI keywords: {e}")
            return f"Error: {e}"

        
"""
# Collection creation purpose
"""
#typesenseDBObj = TypesenseClient()
# typesenseDBObj.appDetailsSchema()
#typesenseDBObj.aiKeywordsSchema()