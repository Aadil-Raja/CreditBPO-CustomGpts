import os
import time
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()
client = OpenAI()  # ✅ No need to manually pass api_key if in .env

# Upload file
FILE_NAME = "knowledge.pdf"
file = client.files.create(file=open(FILE_NAME, "rb"), purpose="assistants")

# Create assistant
assistant = client.beta.assistants.create(
    instructions="Answer questions based on the uploaded PDF.",
    name="PDF Assistant",
    model="gpt-4o",
    tools=[{"type": "file_search"}],
    file_ids=[file.id]  # ✅ this works!
)



assistant_id = assistant.id

# Flask App
app = Flask(__name__)

@app.route("/ask", methods=["POST"])
def ask():
    data = request.json
    question = data.get("question")

    # Create thread
    thread = client.beta.threads.create()

    # Create user message
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=question
    )

    # Run assistant
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id
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

    return jsonify({"answer": answer})


if __name__ == "__main__":
    app.run(debug=True)
