from openai import OpenAI
import shelve
from dotenv import load_dotenv
import os
import time
import logging
import json
import base64

from flask import jsonify, request

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_ASSISTANT_ID = os.getenv('OPENAI_ASSISTANT_ID')

if not OPENAI_API_KEY or not OPENAI_ASSISTANT_ID:
    raise EnvironmentError("Missing OPENAI_API_KEY or OPENAI_ASSISTANT_ID")

client = OpenAI(api_key=OPENAI_API_KEY)


def upload_file(path):
    # Upload a file with an "assistants" purpose
    file = client.files.create(
        file=open("../../data/airbnb-faq.pdf", "rb"), purpose="assistants"
    )


def create_assistant(file):
    """
    You currently cannot set the temperature for Assistant via the API.
    """
    assistant = client.beta.assistants.create(
        name="WhatsApp AirBnb Assistant",
        instructions="You're a helpful WhatsApp assistant that can assist guests that are staying in our Paris AirBnb. Use your knowledge base to best respond to customer queries. If you don't know the answer, say simply that you cannot help with question and advice to contact the host directly. Be friendly and funny.",
        tools=[{"type": "retrieval"}],
        model="gpt-4-1106-preview",
        file_ids=[file.id],
    )
    return assistant


# Use context manager to ensure the shelf file is closed properly
def check_if_thread_exists(wa_id):
    with shelve.open("threads_db") as threads_shelf:
        return threads_shelf.get(wa_id, None)


def store_thread(wa_id, thread_id):
    with shelve.open("threads_db", writeback=True) as threads_shelf:
        threads_shelf[wa_id] = thread_id


def run_assistant(thread, name):
    # Retrieve the Assistant
    assistant = client.beta.assistants.retrieve(OPENAI_ASSISTANT_ID)

    # Run the assistant
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id,
        # instructions=f"You are having a conversation with {name}",
    )

    # Wait for completion
    while run.status != "completed":
        # Be nice to the API
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

    # Retrieve the Messages
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    new_message = messages.data[0].content[0].text.value
    logging.info(f"Generated message: {new_message}")
    return new_message


def generate_response(message_body, wa_id, name, image_path=None):
    # Check if there is already a thread_id for the wa_id
    thread_id = check_if_thread_exists(wa_id)

    # If a thread doesn't exist, create one and store it
    if thread_id is None:
        logging.info(f"Creating new thread for {name} with wa_id {wa_id}")
        thread = client.beta.threads.create()
        store_thread(wa_id, thread.id)
        thread_id = thread.id

    # Otherwise, retrieve the existing thread
    else:
        logging.info(f"Retrieving existing thread for {name} with wa_id {wa_id}")
        thread = client.beta.threads.retrieve(thread_id)
        
        
    # Step 2: Prepare message content
    if image_path:
        message_content = [
            {"type": "text", "text": message_body or "Please describe this image."},
            {"type": "image_url", "image_url": {"url": image_path}}
        ]
    else:
        message_content = message_body
        
    logging.info(f"OpenAI message content:{message_content}")

    # Add message to thread
    message = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message_content,
    )

    # Run the assistant and get the new message
    new_message = run_assistant(thread, name)

    return new_message

def list_assistant():
    try:
        assistants = client.beta.assistants.list()
        assistantList = []
        for assistant in assistants.data:
            item = {
                "id": assistant.id,
                "name": assistant.name,
                "model": assistant.model,
                "description": assistant.description,
                "instructions": assistant.instructions,
            }
            assistantList.append(item)
        return jsonify(assistantList), 200
    except Exception as err:
        logging.error(f"error getting assistant data {err} type {type(err)}")
        return jsonify({"status": "error", "message": "bad request"}), 400

def create_assistant():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400
        logging.info(f"request body: {data}")

    allowed_keys = is_valid_data()
    unknown_keys = set(data.keys()) - allowed_keys
    if unknown_keys:
        return jsonify({"error": f"Unknown fields in request: {list(unknown_keys)}"}), 400

    try:
        # Create an assistant
        assistant = client.beta.assistants.create(
            **{k: v for k, v in data.items() if k in allowed_keys}
        )
            
        logging.info(f"Assistant created: {assistant.name}, ID: {assistant.id}")
        return jsonify({"status": "success", "message": f"Assistant created: {assistant.name}, ID: {assistant.id}"}), 200
    except Exception as err:
        logging.error(f"error getting assistant data {err} type {type(err)}")
        return jsonify({"status": "error", "message": f"bad request{err}"}), 400
       
    
def delete_assistant(assistant_id):
    try:
        if assistant_id:
            # Delete the assistant
            assistant = client.beta.assistants.delete(assistant_id)
            
            logging.info(f"Assistant deleted ID: {assistant.id}")
            return jsonify({"status": "success", "message": f"Assistant deleted ID: {assistant.id}"}), 200
           
        else:
            return jsonify({"status": "error", "message": "invalid body"}), 200
    
    except Exception as err:
        logging.error(f"error getting assistant data {err} type {type(err)}")
        return jsonify({"status": "error", "message": f"bad request{err}"}), 400
    
def update_assistant(assistant_id):
    data = request.get_json()

    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400
       
    logging.info(f"request body: {data}")

    allowed_keys = is_valid_data(data)
    unknown_keys = set(data.keys()) - allowed_keys
    if unknown_keys:
        return jsonify({"error": f"Unknown fields in request: {list(unknown_keys)}"}), 400
        
    # Update an assistant
    try:
        assistant = client.beta.assistants.update(
                assistant_id=assistant_id,
                **{k: v for k, v in data.items() if k in allowed_keys}
        )
                
        logging.info(f"Assistant updated ID: {assistant.id}")
        return jsonify({"status": "success", "message": f"Assistant updated ID: {assistant.id}"}), 200
    except Exception as err:
        logging.error(f"error getting assistant data {err} type {type(err)}")
        return jsonify({"status": "error", "message": f"bad request{err}"}), 400
           
    
def is_valid_data():
    allowed_keys = {'name', 'instructions', 'model', 'tools', 'metadata', 'description'}
    return allowed_keys
           
    