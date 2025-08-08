
import os
import requests
from tqdm import tqdm
import dotenv

dotenv.load_dotenv()

# === CONFIGURATION ===
API_URL = "https://canvas.uva.nl/api/v1"
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
COURSE_ID = 45952  # Causality course

# === HEADERS ===
headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}

# === DOWNLOAD FUNCTION ===
def download_file(file_url, filename, folder):
    response = requests.get(file_url, headers=headers, stream=True)
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    with open(filepath, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

# === GET MODULES ===
def get_modules(course_id):
    url = f"{API_URL}/courses/{course_id}/modules"
    all_modules = []
    page = 1
    
    while True:
        params = {
            'page': page,
            'per_page': 100,  # Get more modules per page
            'include[]': 'items'  # Include module items
        }
        response = requests.get(url, headers=headers, params=params)
        print(f"API Response Status (page {page}): {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error: {response.text}")
            break
            
        modules = response.json()
        if not modules:  # No more modules
            break
            
        all_modules.extend(modules)
        print(f"Page {page}: Found {len(modules)} modules")
        
        # Check if there are more pages
        if len(modules) < 100:
            break
        page += 1
    
    print(f"Total modules found: {len(all_modules)}")
    for i, module in enumerate(all_modules):
        print(f"  Module {i+1}: ID={module.get('id')}, Name='{module.get('name')}', State='{module.get('state')}', Published='{module.get('published')}'")
    
    return all_modules

# === GET MODULE ITEMS ===
def get_module_items(module_id, course_id):
    url = f"{API_URL}/courses/{course_id}/modules/{module_id}/items"
    response = requests.get(url, headers=headers)
    return response.json()

# === GET FILE DETAILS ===
def get_file_info(file_id):
    url = f"{API_URL}/files/{file_id}"
    response = requests.get(url, headers=headers)
    return response.json()

# === MAIN FUNCTION ===
def download_all_module_files(course_id):
    modules = get_modules(course_id)
    print(f"Found {len(modules)} modules.")
    breakpoint()
    for module in modules:
        print(f"📦 Module: {module['name']}")
        items = get_module_items(module["id"], course_id)
        for item in items:
            if item["type"] == "File":
                file_info = get_file_info(item["content_id"])
                file_name = file_info["display_name"]
                file_url = file_info["url"]
                print(f"  ⬇ Downloading: {file_name}")
                download_file(file_url, file_name, folder=f"downloads/{module['name']}")

# === RUN ===
if __name__ == "__main__":
    download_all_module_files(COURSE_ID)