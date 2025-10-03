import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
import json
from typing import Any, Dict, TypedDict, List, Optional
from scrapper import AppDetails

load_dotenv()

class AIKeywords(TypedDict):
    appKeywords: List[str]
    compKeywords: Dict[str, List[str]]

class AIResponse(TypedDict):
    aikeywords: AIKeywords

groq_api_key : str | None = os.getenv("GROQ_API_KEY")
if groq_api_key:
    os.environ["GROQ_API_KEY"] = groq_api_key
else:
    raise ValueError("GROQ_API_KEY environment variable not set.")


# model = init_chat_model("groq:llama3-8b-8192")
# humanMessageData = ""
# messages = [
#     SystemMessage(""" You are a helpful assistant. And brilliant SEO engineer. 
#     Which analyze the given IOS APP category, description and competitor apps 
#     and in response return top 30 keywords for apps and 10 top keywords for its 
#     competitors, and the data in given json format aikeywords:[appKeywords:["keyword1","keyword2"...etc], "compKeywords":{"comp_app1": ["keyword1", "keyword2"...etc], "comp_app2": ["keyword1", "keyword2"...etc}] """),
#     SystemMessage(""" You are a helpful assistant. And brilliant SEO engineer. Which analyze the given IOS APP category, description and competitor apps and in response return top 30 keywords for apps and 10 top keywords for its competitors, and the data in given json format aikeywords:[appKeywords:["keyword1","keyword2"...etc], "compKeywords":{"comp_app1": ["keyword1", "keyword2"...etc], "comp_app2": ["keyword1", "keyword2"...etc}] """),
#     HumanMessage(humanMessageData)
# ]

class AIKeywordGenerator:
    def __init__(self) ->  None:
        self.model = init_chat_model("groq:groq/compound")

    def generateKeywords(self, app_details: AppDetails) -> Optional[AIResponse]:
        system_message = """You are a helpful assistant and a brilliant SEO engineer. 
        Analyze the given iOS app category, description, and competitor apps. 
        In response, return top 30 keywords for the app and 10 top keywords for each of 
        its competitors. The data should be in the following JSON format:
        {
            "aikeywords": {
                "appKeywords": ["keyword1", "keyword2", ...],
                "compKeywords": {
                    "comp_app1_name": ["keyword1", "keyword2", ...],
                    "comp_app2_name": ["keyword1", "keyword2", ...]
                }
            }
        }
        Ensure all keywords are relevant and optimized for App Store Optimization (ASO).
        And do not add generic keyword by any mean 
        Only return the JSON object, with no other text.
        """

        app_name = app_details.get("appname", "N/A")
        app_subtitle = app_details.get("appsubtitle", "N/A")
        category = app_details.get("category", "N/A")
        description = app_details.get("description", "N/A")
        existing_keywords = app_details.get("keywords", [])
        competitor_apps_keywords = app_details.get("competitor_apps_keywords", [])

        competitor_info = {}
        for comp in competitor_apps_keywords:
            competitor_info[comp.get("appname", "Unknown App")] = comp.get("keywords", [])

        human_message_content = f"""
        App Name: {app_name}
        App Subtitle: {app_subtitle}
        Category: {category}
        Description: {description}
        Existing Keywords: {', '.join(existing_keywords)}
        Competitor Apps and their Keywords: {competitor_info}
        """

        messages = [
            SystemMessage(system_message),
            HumanMessage(human_message_content)
        ]

        response = self.model.invoke(messages)
        try:
            # The response content is a string, we need to parse it as JSON
            if isinstance(response.content, str):
                # **FIX**: Clean the response to handle cases where the LLM includes markdown or other text.
                response_text = response.content
                # Find the start and end of the JSON object
                start_index = response_text.find('{')
                end_index = response_text.rfind('}')
                if start_index != -1 and end_index != -1 and end_index > start_index:
                    json_str = response_text[start_index:end_index+1]
                    data = json.loads(json_str)
                else:
                    print(f"Could not find a valid JSON object in the AI response: {response_text}")
                    return None

                # Basic validation to ensure it matches our expected structure
                if "aikeywords" in data and "appKeywords" in data["aikeywords"]:
                    return data
                else:
                    print(f"AI response is missing expected structure: {data}")
                    return None
            return None # Should not happen, but as a fallback
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Failed to decode or validate JSON from AI response: {e}")
            return None