import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import api_keys

def generate_new_token():
    # Define the scopes
    SCOPES = ['https://www.googleapis.com/auth/blogger']
    creds = None
    
    # Check if token.json exists
    if os.path.exists('token.json'):
        try:
            with open('token.json', 'r') as token:
                creds = Credentials.from_authorized_user_info(json.load(token), SCOPES)
        except Exception as e:
            print(f"Error loading existing token: {e}")
            creds = None
    
    # If there are no valid credentials, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Failed to refresh token: {e}")
                creds = None
        
        # If still no valid credentials, start new authorization flow
        if not creds:
            flow = InstalledAppFlow.from_client_config(
                api_keys.BLOGGER_AUTH_KEY, SCOPES)
            creds = flow.run_local_server(port=8090)
        
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            print("New token has been generated and saved to token.json")
    
    return creds

if __name__ == "__main__":
    generate_new_token()
    print("Token generation complete. You can now run your main script.")