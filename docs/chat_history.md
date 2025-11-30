@app.post("/chat")
def chat(user_id: str, message: str):
    if user_id not in active_sessions:
        active_sessions[user_id] = ConversationBufferMemory(return_messages=True)
    
    memory = active_sessions[user_id]