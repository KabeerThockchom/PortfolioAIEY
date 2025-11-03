import logging
import pathlib 
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()
import os
import pandas as pd
import numpy as np
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
)
from azure.identity import DefaultAzureCredential # Recommended for production
import base64 # Needed for image encoding
import mimetypes # To determine image type for base64 encoding
from azure.search.documents.models import VectorizedQuery

# --- Configuration ---
# Azure AI Search Configuration
AZURE_SEARCH_SERVICE_ENDPOINT = "https://aeon-aisearch.search.windows.net" # e.g., https://your-search-service.search.windows.net
AZURE_SEARCH_INDEX_NAME = "rtpa-fund-fact-sheet-new"
# Use AzureKeyCredential for simplicity in example, or DefaultAzureCredential for production
AZURE_SEARCH_ADMIN_KEY = os.getenv("AZURE_SEARCH_ADMIN_KEY", "your-search-admin-key-here")
credential = AzureKeyCredential(AZURE_SEARCH_ADMIN_KEY)
#credential = DefaultAzureCredential() # Assumes you are logged in via Azure CLI or other default methods

# Azure OpenAI Configuration (ensure it matches your PDFProcessor)
AZURE_OPENAI_ENDPOINT = "https://ngtdazureaihub1570085143.openai.azure.com/"
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY", "your-openai-key-here")
AZURE_OPENAI_API_VERSION = "2024-12-01-preview" # Use a version supporting GPT-4o multimodal inputs
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = "text-embedding-3-large" # Deployment name for text-embedding-3-large
AZURE_OPENAI_CHAT_DEPLOYMENT = "gpt-4o" # Deployment name for chat model (must be gpt-4o)

# Embedding Model Configuration
EMBEDDING_DIMENSIONS = 3072 # text-embedding-3-large has 3072 dimensions
EMBEDDING_MODEL_NAME = AZURE_OPENAI_EMBEDDING_DEPLOYMENT
import os
import base64
import mimetypes
import asyncio # Required for async operations

# Azure SDK Imports (using aio versions for async)
from azure.core.credentials import AzureKeyCredential # Use AsyncAzureKeyCredential if directly using keys
# from azure.identity.aio import DefaultAzureCredential # Example if using DefaultAzureCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.search.documents.models import VectorizedQuery

# OpenAI Import (using async version)
from openai import AsyncAzureOpenAI # Use the async client [4][5]


# Use AsyncAzureKeyCredential for async client if using keys
# AZURE_SEARCH_ADMIN_KEY = os.environ.get("AZURE_SEARCH_ADMIN_KEY", "YOUR_SEARCH_ADMIN_KEY")
credential = AzureKeyCredential(AZURE_SEARCH_ADMIN_KEY) # Use AsyncAzureKeyCredential if needed for the specific credential type
# Or use async identity credential:
# from azure.identity.aio import DefaultAzureCredential
# credential = DefaultAzureCredential()


# --- End Credentials ---


class AsyncDocumentIndex:
    def __init__(self, index_name=None, endpoint=None, adminkey=None):
        # Use provided args or fall back to environment variables/defaults
        search_endpoint = endpoint or AZURE_SEARCH_SERVICE_ENDPOINT
        search_index_name = index_name or AZURE_SEARCH_INDEX_NAME
        search_adminkey = adminkey or AZURE_SEARCH_ADMIN_KEY

        # Ensure credential is async compatible if needed (e.g., AsyncAzureKeyCredential)
        # If using DefaultAzureCredential, instantiate its async version
        # from azure.identity.aio import DefaultAzureCredential
        # search_credential = AsyncAzureKeyCredential(search_adminkey) # Or DefaultAzureCredential()

        # NOTE: Ensure the 'credential' object below is suitable for async operations.
        # If you initialized 'credential' globally using a sync credential type,
        # you MUST re-initialize it here using the corresponding async type,
        # e.g., AsyncAzureKeyCredential(search_adminkey)
        search_credential = AzureKeyCredential(search_adminkey) # Replace if async key credential needed
        # search_credential = DefaultAzureCredential() # If using managed identity etc.


        # Use AsyncAzureOpenAI client [5]
        self.openai_client = AsyncAzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_KEY,
            api_version=AZURE_OPENAI_API_VERSION
        )

        # Use Azure AI Search Async Clients [6]
        self.index_client = SearchIndexClient(endpoint=search_endpoint, credential=search_credential)
        self.search_client = SearchClient(endpoint=search_endpoint, index_name=search_index_name, credential=search_credential)
        print("Initialized Async Clients")

    # This method performs local file I/O - kept synchronous for simplicity
    # Use libraries like aiofiles if this needs to be fully non-blocking
    def encode_image_to_base64(self, image_path):
        """Encodes an image file to a base64 string with MIME type."""
        if not image_path or not os.path.exists(image_path):
            print(f"Warning: Image path not found or invalid: {image_path}")
            return None
        try:
            mime_type, _ = mimetypes.guess_type(image_path)
            if not mime_type or not mime_type.startswith('image'):
                # Fallback logic for common types if guess fails
                ext = os.path.splitext(image_path)[1].lower()
                if ext == ".png": mime_type = "image/png"
                elif ext in [".jpg", ".jpeg"]: mime_type = "image/jpeg"
                elif ext == ".webp": mime_type = "image/webp"
                elif ext == ".gif": mime_type = "image/gif"
                else:
                    print(f"Warning: Unknown image type for {image_path}. Skipping encoding.")
                    return None

            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                return f"data:{mime_type};base64,{encoded_string}"
        except Exception as e:
            print(f"Error encoding image {image_path}: {e}")
            return None

    async def generate_embeddings_async(self, text_to_embed): # Added async
        """Generates embeddings for the given text using Azure OpenAI."""
        try:
            # Use await for the async client call [5]
            response = await self.openai_client.embeddings.create(
                input=text_to_embed,
                model=EMBEDDING_MODEL_NAME
            )
            embedding_vector = response.data[0].embedding
            # Ensure embedding is list of floats
            if isinstance(embedding_vector, list) and all(isinstance(x, float) for x in embedding_vector):
                return embedding_vector
            else:
                # Attempt conversion if needed, though SDK usually returns floats
                return [float(x) for x in embedding_vector]
        except Exception as e:
            print(f"Error generating embeddings: {e}")
            return None

    async def query_index_async(self, query_text, ticker, k=12): # Added async
        """Performs a vector search on the index and returns the top k results."""
        # Use await for the async embedding generation
        query_embedding = await self.generate_embeddings_async(query_text)
        if not query_embedding:
            print("Could not generate embedding for the query.")
            return []

        vector_query = VectorizedQuery(
            vector=query_embedding,
            k_nearest_neighbors=k,
            fields="embedding" # Field containing the vector
        )

        print(f"Performing async vector search for: '{query_text}' (top {k})")
        try:
            # Use await for the async search call [3]
            results = await self.search_client.search(
                search_text=None, # Use None for vector-only search
                vector_queries=[vector_query],
                select=["id", "content", "file_name", "page_info", "source_type", "image_path"]
            )

            retrieved_results = []
            # Use 'async for' to iterate over async results [3]
            async for result in results:
                print("Image Path:", result.get("image_path", "No image path"))
                if ticker and ticker.lower() not in result.get("file_name", "").lower():
                    continue
                retrieved_results.append({
                    "id": result["id"],
                    "score": result["@search.score"],
                    "content": result["content"],
                    "file_name": result["file_name"],
                    "page_info": result["page_info"],
                    "source_type": result["source_type"],
                    "image_path": result.get("image_path", None) # Use .get for safety
                })

            print(f"Retrieved {len(retrieved_results)} results asynchronously.")
            return retrieved_results
        except Exception as e:
             print(f"Error during async search: {e}")
             return []

    async def get_multimodal_rag_response_async(self, user_query, search_results): # Added async
        """Formats search results (text/images) and sends them to GPT-4o for a RAG response asynchronously."""
        if not search_results:
            return "I couldn't find any relevant information in the documents."

        system_prompt = """You are an AI assistant designed for multimodal Retrieval-Augmented Generation (RAG).
    Answer the user's query based *ONLY* on the provided text sources and images.
    Analyze both the text snippets and the visual content of the images.
    Be concise,helpful,short and crisp as your answer will be used in IVR call which is audio based don't use special characters. If the answer cannot be determined from the provided sources, state that clearly.
    Do not use any prior knowledge or external information.
    Just return the answer dont cite sources."""

        user_message_content = []
        user_message_content.append({
            "type": "text",
            "text": f"Please answer the following query based *only* on the provided sources (text and images below):\n\nQuery: {user_query}\n\n--- Sources ---"
        })

        sources_summary = []
        image_sources_added = 0
        max_images_to_send = 5

        for i, res in enumerate(search_results):
            source_id = res.get('id', f'unknown_{i}')
            source_type = res.get('source_type', 'unknown')
            content = res.get('content', '')
            file_info = f"File: {res.get('file_name', 'N/A')}, Page(s): {res.get('page_info', 'N/A')}"

            if source_type == "text":
                user_message_content.append({
                    "type": "text",
                    "text": f"\n\nText Source [{source_id}] ({file_info}):\n{content}"
                })
                sources_summary.append(f"[{source_id}] Text: {content[:100]}...")
            elif source_type == "figure" and res.get('image_path'):
                if image_sources_added < max_images_to_send:
                    # Get the raw path string
                    raw_path_str = res["image_path"]
                    # Replace backslashes with forward slashes
                    normalized_path_str = raw_path_str.replace("\\", "/")
                    
                    # --- Optional but Recommended: Use pathlib ---
                    image_path = pathlib.Path(normalized_path_str)
                    # NOTE: encode_image_to_base64 is still synchronous here
                    base64_image_data = self.encode_image_to_base64(image_path)

                    if base64_image_data:
                        user_message_content.append({
                            "type": "text",
                            "text": f"\n\nFigure Source [{source_id}] ({file_info}):\nCaption/Description: {content}\nImage:"
                        })
                        user_message_content.append({
                            "type": "image_url",
                            "image_url": {"url": base64_image_data, "detail": "auto"}
                        })
                        sources_summary.append(f"[{source_id}] Figure: {content[:100]}... (Image Sent)")
                        image_sources_added += 1
                    else:
                        user_message_content.append({
                            "type": "text",
                            "text": f"\n\nFigure Source [{source_id}] ({file_info}):\nCaption/Description: {content}\n(Image could not be loaded)"
                        })
                        sources_summary.append(f"[{source_id}] Figure: {content[:100]}... (Image Failed)")
                else:
                    user_message_content.append({
                        "type": "text",
                        "text": f"\n\nFigure Source [{source_id}] ({file_info}):\nCaption/Description: {content}\n(Image limit reached, not sending image data)"
                    })
                    sources_summary.append(f"[{source_id}] Figure: {content[:100]}... (Image Limit Reached)")
            else:
                user_message_content.append({
                    "type": "text",
                    "text": f"\n\nSource [{source_id}] ({file_info}, Type: {source_type}):\n{content}"
                })
                sources_summary.append(f"[{source_id}] {source_type}: {content[:100]}...")

        user_message_content.append({
            "type": "text",
            "text": "\n\n--- End of Sources ---\n\nBased *only* on the text and images provided above, answer the initial query." # Removed citation instruction based on system prompt
        })

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message_content}
        ]

        try:
            print(f"Sending async query, {len([s for s in sources_summary if 'Text:' in s])} text sources, and {image_sources_added} images to GPT-4o...")

            # Use await for the async chat completion call [2][4][5]
            response = await self.openai_client.chat.completions.create(
                model=AZURE_OPENAI_CHAT_DEPLOYMENT,
                messages=messages,
                temperature=0.1,
                max_tokens=1500
            )

            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content.strip()
            else:
                finish_reason = response.choices[0].finish_reason if response.choices else "unknown"
                print(f"Warning: Received no content. Finish reason: {finish_reason}")
                # Add filter results logging if needed
                # ... (filter results logging as in original code) ...
                return "Error: Received an empty or filtered response from the language model."

        except Exception as e:
            print(f"Error calling Azure OpenAI Chat API (GPT-4o) asynchronously: {e}")
            return "Error: Could not get a response from the language model due to an API error."

    async def close_clients(self):
        """Close the async clients."""
        if self.openai_client:
             await self.openai_client.close()
        if self.search_client:
            await self.search_client.close()
        if self.index_client:
            await self.index_client.close()
        print("Closed Async Clients")