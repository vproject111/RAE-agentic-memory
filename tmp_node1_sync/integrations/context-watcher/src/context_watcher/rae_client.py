import os

import httpx

from .config import settings


class RAEClient:
    def __init__(self, tenant_id: str):
        self.api_url = settings.RAE_API_URL
        self.headers = {
            "X-API-Key": settings.RAE_API_KEY,
            "X-Tenant-Id": tenant_id,
        }
        self.base_v1_url = f"{self.api_url}/v1"

    def store_file_memory(self, file_path: str):
        """
        Reads a file and stores its content as a memory in the RAE API.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return

        if not content.strip():
            return

        file_name = os.path.basename(file_path)
        _, file_extension = os.path.splitext(file_name)

        payload = {
            "content": content,
            "source": file_path,
            "layer": "ltm",
            "tags": [file_extension.strip("."), "file-watcher"],
        }

        try:
            with httpx.Client() as client:
                response = client.post(
                    f"{self.base_v1_url}/memory/store",
                    json=payload,
                    headers=self.headers,
                )
                response.raise_for_status()
                print(f"Successfully stored memory for file: {file_path}")
                return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Error storing memory for source {file_path}: {e.response.text}")
        except Exception as e:
            print(f"An unexpected error occurred while storing memory: {e}")

    def query_memory(self, query_text: str, k: int = 10):
        """
        Queries the RAE API for relevant memories.
        """
        payload = {"query_text": query_text, "k": k}
        try:
            with httpx.Client() as client:
                response = client.post(
                    f"{self.base_v1_url}/memory/query",
                    json=payload,
                    headers=self.headers,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Error querying memory: {e.response.text}")
        except Exception as e:
            print(f"An unexpected error occurred while querying memory: {e}")
        return None

    def delete_memory(self, memory_id: str):
        """
        Deletes a memory from the RAE API.
        """
        try:
            with httpx.Client() as client:
                response = client.delete(
                    f"{self.base_v1_url}/memory/delete?memory_id={memory_id}",
                    headers=self.headers,
                )
                response.raise_for_status()
                print(f"Successfully deleted memory: {memory_id}")
                return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Error deleting memory {memory_id}: {e.response.text}")
        except Exception as e:
            print(f"An unexpected error occurred while deleting memory: {e}")
