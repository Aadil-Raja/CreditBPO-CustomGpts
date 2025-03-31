import os
import time
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from openai import OpenAI
from utilities import cleanMessage

# Load environment variables
load_dotenv()
client = OpenAI()  # ✅ No need to manually pass api_key if in .env
# FILE_ID = os.getenv("FILE_ID")

# Directory containing the files to upload
UPLOAD_FOLDER = "knowledge"  # Change this to your actual folder

# Load existing file IDs from .env
FILE_IDS = os.getenv("FILE_IDS", "").split(",")

# If no file IDs exist, upload files from the folder
if not FILE_IDS or FILE_IDS == [""]:
    uploaded_file_ids = []
    
    # Get all PDF files in the folder
    pdf_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith(".pdf")]

    if not pdf_files:
        raise ValueError("No PDF files found in the specified folder.")

    # Upload each file and store the IDs
    for pdf in pdf_files:
        file_path = os.path.join(UPLOAD_FOLDER, pdf)
        file = client.files.create(file=open(file_path, "rb"), purpose="assistants")
        uploaded_file_ids.append(file.id)
        print(f"Uploaded {pdf}: {file.id}")

    # Save the new FILE_IDS in the environment (manual step for persistence)
    FILE_IDS = uploaded_file_ids
    print(f"Files uploaded! Save these FILE_IDS in .env: {','.join(FILE_IDS)}")


# # Upload file
# FILE_NAME = "knowledge.pdf"

# if not FILE_IDS:
#     file = client.files.create(file=open(FILE_NAME, "rb"), purpose="assistants")
#     FILE_ID = file.id
#     print(f"File uploaded! Save this FILE_ID in .env: {FILE_ID}")

# Create assistant
# assistant = client.beta.assistants.create(
#     instructions="Answer questions based on the uploaded PDF.",
#     name="PDF Assistant",
#     model="gpt-4o",
#     tools=[{"type": "file_search"}],
#     file_ids=[file.id]  # ✅ this works!
# )

# Create vector store
# {vector_store = client.beta.vector_stores.create(name="CreditBPO Knowledge Base")

# # Prepare file streams
# file_streams = []
# knowledge_folder = "knowledge"

# for filename in os.listdir(knowledge_folder):
#     file_path = os.path.join(knowledge_folder, filename)
#     if os.path.isfile(file_path):
#         file_streams.append(open(file_path, "rb"))

# # Upload files to vector store
# file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
#     vector_store_id=vector_store.id,
#     files=file_streams
# )}

ASSISTANT_ID = os.getenv("ASSISTANT_ID")

if not ASSISTANT_ID:
    with open("instructions.txt", "r", encoding="utf-8") as file:
        instructions = file.read()
    assistant = client.beta.assistants.create(
    # instructions="Answer questions based on the uploaded PDF.",
    instructions=instructions,
    name="CreditBPO Lead Converter",
    model="gpt-4o-mini",
    tools=[{"type": "file_search"}],
    tool_resources={
        "file_search": {
            "file_ids": FILE_IDS  # your actual file IDs here
        }
    }
    )
    ASSISTANT_ID = assistant.id
    print(f"Assistant created! Save this ASSISTANT_ID in .env: {ASSISTANT_ID}")


# Flask App
app = Flask(__name__)

@app.route("/ask", methods=["POST"])
def ask():
    data = request.json
    question = data.get("question")

    # Create thread
    thread = client.beta.threads.create()

    attachments = [{"file_id": file_id.strip(), "tools": [{"type": "file_search"}]} for file_id in FILE_IDS]

    # Create user message
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=question,
        attachments=attachments
        # attachments=[{"file_id": FILE_ID, "tools": [{"type": "file_search"}]}]
    )

    # Run assistant
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=ASSISTANT_ID
    )

    # Wait for completion
    while True:
        status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if status.status == "completed":
            break
        time.sleep(1)

    # Get messages
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    answer = messages.data[0].content[0].text.value

    # print(messages)

    # message_content = messages.data[0].content[0].text
    # annotations = message_content.annotations
    # citations = []

    # # Iterate over the annotations and add footnotes
    # for index, annotation in enumerate(annotations):
    #     # Replace the text with a footnote
    #     message_content.value = message_content.value.replace(annotation.text, f' [{index}]')
        
    #     # Gather citations based on annotation attributes
    #     if (file_citation := getattr(annotation, 'file_citation', None)):
    #         cited_file = client.files.retrieve(file_citation.file_id)
    #         citations.append(f'[{index}] {file_citation.quote} from {cited_file.filename}')
    #     elif (file_path := getattr(annotation, 'file_path', None)):
    #         cited_file = client.files.retrieve(file_path.file_id)
    #         citations.append(f'[{index}] Click <here> to download {cited_file.filename}')
    #         # Note: File download functionality not implemented above for brevity

    # # Add footnotes to the end of the message before displaying to user
    # print(message_content)
    # message_content.value += '\n' + '\n'.join(citations)

    cleanedMessage = cleanMessage(answer)

    return jsonify({"answer": answer, "message": cleanedMessage})


if __name__ == "__main__":
    app.run(debug=True)
