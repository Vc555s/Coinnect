import requests
import json
import os
import base64

class IPFSService:
    def __init__(self):
        # Filebase IPFS endpoint
        self.base_url = "https://api.filebase.io/v1/ipfs"
        
        # Your Filebase access key and secret key
        # These should be stored in environment variables in production
        self.access_key = os.environ.get('FILEBASE_ACCESS_KEY', 'your_access_key_here')
        self.secret_key = os.environ.get('FILEBASE_SECRET_KEY', 'your_secret_key_here')
        
        # Set up basic authentication
        self.auth = self._get_basic_auth()
        
    def _get_basic_auth(self):
        # Create basic auth header from access and secret keys
        auth_string = f"{self.access_key}:{self.secret_key}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        return f"Basic {encoded_auth}"
    
    def add_json_to_ipfs(self, json_data):
        """Add JSON data to IPFS via Filebase"""
        try:
            # Convert Python dict to JSON string
            json_str = json.dumps(json_data)
            
            # Set up the request headers
            headers = {
                'Authorization': self.auth,
                'Content-Type': 'application/json'
            }
            
            # Make the API request to add the content to IPFS
            response = requests.post(
                f"{self.base_url}/add", 
                data=json_str,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                # Return the IPFS hash (CID)
                return result.get('Hash')
            else:
                return {"error": f"Failed to add to IPFS: {response.status_code} - {response.text}"}
        
        except Exception as e:
            return {"error": f"Exception when adding to IPFS: {str(e)}"}
    
    def get_json_from_ipfs(self, ipfs_hash):
        """Get JSON data from IPFS via Filebase"""
        try:
            # Set up the request headers
            headers = {
                'Authorization': self.auth
            }
            
            # Make the API request to get the content from IPFS
            response = requests.get(
                f"{self.base_url}/cat?arg={ipfs_hash}", 
                headers=headers
            )
            
            if response.status_code == 200:
                # Parse the JSON response
                try:
                    return json.loads(response.text)
                except json.JSONDecodeError:
                    return {"error": "Could not decode JSON from IPFS response"}
            else:
                return {"error": f"Failed to get from IPFS: {response.status_code} - {response.text}"}
        
        except Exception as e:
            return {"error": f"Exception when getting from IPFS: {str(e)}"}
    
    def pin_hash(self, ipfs_hash):
        """Pin an IPFS hash to ensure it persists in Filebase storage"""
        try:
            headers = {
                'Authorization': self.auth
            }
            
            response = requests.post(
                f"{self.base_url}/pin/add?arg={ipfs_hash}", 
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                return result
            else:
                return {"error": f"Failed to pin hash: {response.status_code} - {response.text}"}
        
        except Exception as e:
            return {"error": f"Exception when pinning hash: {str(e)}"}
    
    def upload_file_to_ipfs(self, file_path):
        """Upload a file to IPFS via Filebase"""
        try:
            # Check if file exists
            if not os.path.isfile(file_path):
                return {"error": "File not found"}
            
            headers = {
                'Authorization': self.auth
            }
            
            # Open the file in binary mode and send it
            with open(file_path, 'rb') as file:
                files = {'file': file}
                response = requests.post(
                    f"{self.base_url}/add", 
                    files=files,
                    headers=headers
                )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('Hash')
            else:
                return {"error": f"Failed to upload file: {response.status_code} - {response.text}"}
        
        except Exception as e:
            return {"error": f"Exception when uploading file: {str(e)}"}
