import os
import time
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from openai import OpenAI
from utilities import cleanMessage

# Load environment variables
load_dotenv()
client = OpenAI()

# Setup
UPLOAD_FOLDER = "knowledge"
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID")

# Upload files to vector store or create a new one
if not VECTOR_STORE_ID:
    # Create vector store
    vector_store = client.vector_stores.create(name="CreditBPO Vector Store")
    VECTOR_STORE_ID = vector_store.id
    print(f"Vector store created! Save this VECTOR_STORE_ID in .env: {VECTOR_STORE_ID}")

    # Ready file streams
    file_paths = [os.path.join(UPLOAD_FOLDER, f) for f in os.listdir(UPLOAD_FOLDER) if f.endswith(".pdf")]
    if not file_paths:
        raise ValueError("No PDF files found in knowledge1 folder.")
    file_streams = [open(path, "rb") for path in file_paths]

    # Upload and poll
    file_batch = client.vector_stores.file_batches.upload_and_poll(
        vector_store_id=VECTOR_STORE_ID,
        files=file_streams
    )

    print(file_batch.status)
    print(file_batch.file_counts)
    assistant = client.beta.assistants.update(
    assistant_id=ASSISTANT_ID,
  tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
)
else:
    print("VECTOR_STORE_ID found in .env. Skipping vector store creation.")

# Create assistant if not present
if not ASSISTANT_ID:
    with open("instructions.txt", "r", encoding="utf-8") as file:
        instructions = file.read()
    assistant = client.beta.assistants.create(
        instructions=instructions,
        name="CreditBPO Lead Converter",
        model="gpt-4-turbo",
        tools=[{"type": "file_search"}],
        # tool_resources={
        #     "file_search": {
        #         "vector_store_ids": [VECTOR_STORE_ID]
        #     }
        # }
    )
    ASSISTANT_ID = assistant.id
    print(f"Assistant created! Save this ASSISTANT_ID in .env: {ASSISTANT_ID}")

# Flask App
app = Flask(__name__)

@app.route("/ask", methods=["POST"])
def ask():
    data = request.json
    question = data.get("question")

    # Create a thread
    thread = client.beta.threads.create()

    # Create a message
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=question
    )

    # Run assistant
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=ASSISTANT_ID
    )

    # Wait until run completes
    while True:
        status = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )
        if status.status == "completed":
            break
        time.sleep(1)

    # Get the answer
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    answer = messages.data[0].content[0].text.value
    cleanedMessage = cleanMessage(answer)

    return jsonify({"answer": answer, "message": cleanedMessage})

if __name__ == "__main__":
    app.run(debug=True)