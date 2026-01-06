import uuid
from fastapi import APIRouter, HTTPException, Header, Request, Depends
from shared.snowflake.client import SnowflakeClient
# from app.models.auth import StartAuthRequest
router = APIRouter()

def get_db(request: Request): # Dependency to get SnowflakeClient, from app main state
    return request.app.state.snowflake_client


@router.get("/conversations")
def get_all_conversations(authorization: str = Header(None), db = Depends(get_db)):
    # 1. Check if the header exists
    if not authorization:
        raise HTTPException(status_code=401, detail="No Authorization header found")

    # 2. Extract the actual token string
    # authorization will look like "Bearer <token_string>"
    try:
        token = authorization.split(" ")[1]
    except IndexError:
        raise HTTPException(status_code=401, detail="Invalid header format")

    # 3. TODO: Use the token to identify the user
    # (For now, we use a placeholder, but later you can decode this)
    user_id = "BEETLE" 

    res = db.execute(f""" SELECT id, title
                       FROM CONVERSATIONS 
                       WHERE user_id = '{user_id}'
                       ORDER BY created_at DESC
                   """, fetch="all")
    
    return [{"id": row[0], "title": row[1]} for row in res]

@router.get("/conversations/{conversation_id}/messages")
def get_messages(conversation_id: str, db = Depends(get_db)):
    # TODO: Execute query in Snowflake...
    # This query fetches all past messages for the sidebar click
    # query = """
    # SELECT role, content, created_at 
    # FROM MESSAGES 
    # WHERE conversation_id = %s 
    # ORDER BY created_at ASC
    # """

    res = db.execute(f""" SELECT role, content, created_at
                       FROM MESSAGES 
                       WHERE conversation_id = '{conversation_id}'
                       ORDER BY created_at ASC
                   """, fetch="all")
    messages_list = [{"role": row[0], "content": row[1], "created_at": row[2]} for row in res]

    # For now, return a mock list:
    return messages_list


@router.post("/conversations")
def create_conversation(payload: dict, authorization: str = Header(None)):
    """Create a new conversation for the user."""
    if not authorization:
        raise HTTPException(status_code=401, detail="No Authorization header found")

    try:
        token = authorization.split(" ")[1]
    except IndexError:
        raise HTTPException(status_code=401, detail="Invalid header format")

    user_id = "BEETLE" # Placeholder; later decode the token

    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")

    # Generate a new conversation ID
    conv_id = str(uuid.uuid4())
    title = payload.get("title", "New Conversation")

    return {"id": conv_id, "title": title}


@router.post("/send")
def handle_chat(payload: dict, authorization: str = Header(None), db = Depends(get_db)): # TODO: Define payload model
    """Handle sending a message and getting AI response."""

    conv_id = payload.get("conversation_id") # Might be null if it's a new chat
    message_text = payload.get("message")

    # If no conv_id, this is the FIRST message of a new chat
    if not conv_id:
        conv_id = str(uuid.uuid4())
        # SQL: INSERT INTO CONVERSATIONS (id, user_id, title) 
        #      VALUES ({conv_id}, {user_id}, {message_text[:30]})
        db.execute(f"""
            INSERT INTO CONVERSATIONS (id, user_id, title) 
            VALUES ('{conv_id}', 'BEETLE', '{" ".join(message_text[:27].split()[:-1])}...')
        """)
    
    # SQL: INSERT INTO MESSAGES (conversation_id, role, content) 
    #      VALUES ({conv_id}, 'user', {message_text})

    db.execute(f"""
        INSERT INTO MESSAGES (conversation_id, role, content) 
        VALUES ('{conv_id}', 'user', '{message_text}')
    """)
    
    # ... Get AI Response ...
    import random
    random_id = random.randint(1000, 9999)
    ai_response = f"This is a mocked AI response with id {random_id}"

    db.execute(f"""
        INSERT INTO MESSAGES (conversation_id, role, content) 
        VALUES ('{conv_id}', 'assistant', '{ai_response}')
    """)
    
    # SQL: INSERT INTO MESSAGES (conversation_id, role, content) 
    #      VALUES ({conv_id}, 'assistant', {ai_response})
    
    return {
        "conversation_id": conv_id,
        "message": ai_response
    }