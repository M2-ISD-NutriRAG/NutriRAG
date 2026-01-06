import hashlib
import uuid
from fastapi import APIRouter, HTTPException, Header, Request, Depends
from shared.snowflake.client import SnowflakeClient
# from app.models.auth import StartAuthRequest
router = APIRouter()

def get_db(request: Request): # Dependency to get SnowflakeClient, from app main state
    return request.app.state.snowflake_client

def get_current_user(authorization: str = Header(None), db = Depends(get_db)):
    # 1. Check if the header exists
    if not authorization:
        raise HTTPException(status_code=401, detail="No Authorization header found")

    # 2. Extract the actual token string
    try:
        token = authorization.split(" ")[1]
    except IndexError:
        raise HTTPException(status_code=401, detail="Invalid header format")

    token_hash = hashlib.sha256(token.encode()).hexdigest()
    # user = db.execute(f"SELECT username FROM USER_SESSIONS WHERE token_hash = '{token_hash}'", fetch="one")
    user = db.execute(f"SELECT username FROM USER_SESSIONS WHERE token_hash = %s", params=(token_hash,), fetch="one")
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user[0]


@router.get("/conversations")
def get_all_conversations(authorization: str = Header(None), db = Depends(get_db), username: str = Depends(get_current_user)):
    res = db.execute(f""" SELECT id, title
                       FROM CONVERSATIONS 
                       WHERE user_id = '{username}'
                       ORDER BY created_at DESC
                   """, fetch="all")
    
    return [{"id": row[0], "title": row[1]} for row in res]

@router.get("/conversations/{conversation_id}/messages")
def get_messages(conversation_id: str, authorization: str = Header(None), db = Depends(get_db), username: str = Depends(get_current_user)):
    can_access = db.execute(f""" SELECT id
                   FROM CONVERSATIONS 
                   WHERE id = '{conversation_id}' AND user_id = '{username}'
               """, fetch="one")
    if not can_access:
        raise HTTPException(status_code=403, detail="Access denied to this conversation")

    res = db.execute(f""" SELECT role, content, created_at
                       FROM MESSAGES 
                       WHERE conversation_id = %s
                       ORDER BY created_at ASC
                   """, params=(conversation_id,), fetch="all")

    messages_list = [{"role": row[0], "content": row[1], "created_at": row[2]} for row in res]

    # For now, return a mock list:
    return messages_list


@router.post("/conversations")
def create_conversation(payload: dict, authorization: str = Header(None), db = Depends(get_db), username: str = Depends(get_current_user)):
    """Create a new conversation for the user."""
    _ = username # Just to ensure user is valid

    conv_id = str(uuid.uuid4()) # Generate a new conversation ID
    title = payload.get("title", "New Conversation")

    return {"id": conv_id, "title": title}

@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, authorization: str = Header(None), db = Depends(get_db), username: str = Depends(get_current_user)):
    """Delete a conversation and its messages."""
    can_access = db.execute(f""" SELECT id
                   FROM CONVERSATIONS 
                   WHERE id = '{conversation_id}' AND user_id = '{username}'
               """, fetch="one")
    if not can_access:
        raise HTTPException(status_code=403, detail="Access denied to this conversation")
    db.execute(f""" DELETE FROM MESSAGES 
                    WHERE conversation_id = %s
                """, params=(conversation_id,))
    db.execute(f""" DELETE FROM CONVERSATIONS 
                    WHERE id = %s
                """, params=(conversation_id,))
    return {"ok": True}


@router.post("/send")
def handle_chat(payload: dict, authorization: str = Header(None), db = Depends(get_db), username: str = Depends(get_current_user)):
    """Handle sending a message and getting AI response."""

    conv_id = payload.get("conversation_id") # Might be null if it's a new chat
    message_text = payload.get("message")


    # If no conv_id, this is the FIRST message of a new chat
    if not conv_id:
        conv_id = str(uuid.uuid4())
        print('INSERT INTO CONVERSATIONS', conv_id, message_text)
        db.execute(f"""
            INSERT INTO CONVERSATIONS (id, user_id, title) 
            VALUES (%s, %s, %s)
        """, params=(conv_id, username, (" ".join(message_text[:27].split()[:-1]) if " " in message_text else "New Conversation") + "..."))
        

    db.execute(f"""
        INSERT INTO MESSAGES (conversation_id, role, content) 
        VALUES (%s, %s, %s)
    """, params=(conv_id, 'user', message_text))
    
    # ... Get AI Response ...

    # HERE @Tiphaine

    import random
    random_id = random.randint(1000, 9999)
    ai_response = f"This is a mocked AI response with id {random_id}"


    # Add AI response to conversation history
    db.execute(f"""
        INSERT INTO MESSAGES (conversation_id, role, content) 
        VALUES (%s, %s, %s)
    """, params=(conv_id, 'assistant', ai_response))

    return {
        "conversation_id": conv_id,
        "message": ai_response
    }