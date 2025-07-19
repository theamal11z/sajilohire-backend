import requests
from config import settings

class PhantomBusterService:
    def __init__(self):
        self.base_url = settings.PHANTOMBUSTER_BASE_URL
        self.api_key = settings.PHANTOMBUSTER_API_KEY

    def get_headers(self):
        return {
            "X-Phantombuster-Key-1": self.api_key,
            "Content-Type": "application/json"
        }

    def fetch_linkedIn_data(self, profile_url):
        endpoint = f"{self.base_url}/agents/launch"
        params = {
            "agentId": "INSERT_YOUR_AGENT_ID_HERE",
            "argument": {
                "profileUrl": profile_url
            }
        }
        response = requests.post(endpoint, headers=self.get_headers(), json=params)
        return response.json()

    def fetch_social_media_data(self, profile_url):
        # Similar method to fetch social media data
        pass
