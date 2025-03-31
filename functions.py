import os
import json
import requests
from openai import OpenAI
from prompts import assistant_instructions
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GOOGLE_CLOUD_API_KEY = os.getenv('GOOGLE_CLOUD_API_KEY')
AIRTABLE_API_KEY = os.getenv('AIRTABLE_API_KEY')

def create_lead(name, phone, address):
    url = "https://api.airtable.com/v0/your_base_id/Leads"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "records": [{
            "fields": {
                "Name": name,
                "Phone": phone,
                "Address": address
            }
        }]
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()

def get_coordinates(address):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={GOOGLE_CLOUD_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        location = response.json()['results'][0]['geometry']['location']
        return location['lat'], location['lng']
    return None, None

def get_solar_data(lat, lng):
    url = f"https://solar.googleapis.com/v1/buildingInsights:findClosest?location.latitude={lat}&location.longitude={lng}&requiredQuality=HIGH&key={GOOGLE_CLOUD_API_KEY}"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else {}

def extract_financial_analyses(solar_data):
    return solar_data.get('solarPotential', {}).get('financialAnalyses', [])

def get_financial_data_for_address(address):
    lat, lng = get_coordinates(address)
    solar_data = get_solar_data(lat, lng)
    return extract_financial_analyses(solar_data)

def create_assistant(client):
    assistant_file = "assistant.json"
    if os.path.exists(assistant_file):
        with open(assistant_file, 'r') as f:
            return json.load(f)["assistant_id"]

    file = client.files.create(
        file=open("knowledge.docx", "rb"),
        purpose='assistants'
    )

    assistant = client.beta.assistants.create(
        instructions=assistant_instructions,
        model="gpt-4-1106-preview",
        tools=[
            { "type": "retrieval" },
            {
                "type": "function",
                "function": {
                    "name": "solar_panel_calculations",
                    "description": "Estimate savings using solar data.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "address": {"type": "string"},
                            "monthly_bill": {"type": "integer"}
                        },
                        "required": ["address", "monthly_bill"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_lead",
                    "description": "Save lead to Airtable CRM.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "phone": {"type": "string"},
                            "address": {"type": "string"}
                        },
                        "required": ["name", "phone", "address"]
                    }
                }
            }
        ],
        file_ids=[file.id]
    )

    with open(assistant_file, 'w') as f:
        json.dump({"assistant_id": assistant.id}, f)

    return assistant.id
