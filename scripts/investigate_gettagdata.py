import json
import os

import requests

# --- Configuration ---
# The script will try to get the configuration from environment variables.
# If they are not found, it will use the placeholder values.
# Please replace the placeholder values if you are not using environment variables.
API_URL = os.environ.get(
    "CANARY_VIEWS_BASE_URL", "https://scunscanary.secil.pt:55236/api"
)
API_TOKEN = os.environ.get("CANARY_API_TOKEN", "63c9a371-2768-4730-9416-28a42d5ac36e")
VIEW_NAME = os.environ.get("x CANARY_VIEW_NAME", "localhost")
TAG_NAME = f"{VIEW_NAME}.{{Diagnostics}}.Sys.Memory Physical"  # {{Diagnostics}} is a placeholder
API_VERSION = "v2"

# --- Request Parameters ---
params = {
    "apiToken": API_TOKEN,
    "tags": TAG_NAME,
    "startTime": "now-1h",
    "endTime": "now",
    "maxSize": 10,
}


# --- Helper Function ---
def make_request(method, endpoint, request_params):
    """Makes a request to the Canary API and prints the response."""
    headers = {"Content-Type": "application/json"}
    try:
        if method.upper() == "GET":
            response = requests.get(
                f"{API_URL}/{API_VERSION}/{endpoint}",
                params=request_params,
                headers=headers,
            )
        elif method.upper() == "POST":
            # For POST, the `tags` parameter is expected to be a list
            post_params = request_params.copy()
            post_params["tags"] = [post_params["tags"]]
            response = requests.post(
                f"{API_URL}/{API_VERSION}/{endpoint}", json=post_params, headers=headers
            )
        else:
            print(f"Unsupported method: {method}")
            return

        response.raise_for_status()  # Raise an exception for bad status codes
        print(f"--- Response from {endpoint} ({method}) ---")
        print(json.dumps(response.json(), indent=2))
        print("-" * (len(endpoint) + 20))

    except requests.exceptions.RequestException as e:
        print(f"Error calling {endpoint}: {e}")
        # print response text for more details on the error
        if e.response is not None:
            print(f"Response text: {e.response.text}")
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {endpoint}. Response content:")
        print(response.text)


# --- Investigation ---
if __name__ == "__main__":
    print("Investigating getTagData vs getTagData2...")
    print("PARAMS:", params)

    # --- Call getTagData ---
    print("\nCalling getTagData (GET)...")
    make_request("GET", "getTagData", params)

    print("\nCalling getTagData (POST)...")
    make_request("POST", "getTagData", params)

    # --- Call getTagData2 ---
    print("\nCalling getTagData2 (GET)...")
    make_request("GET", "getTagData2", params)

    print("\nCalling getTagData2 (POST)...")
    make_request("POST", "getTagData2", params)
