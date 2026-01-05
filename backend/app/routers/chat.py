from fastapi import APIRouter #, HTTPException
# from app.models.auth import StartAuthRequest


router = APIRouter()


@router.get("/conversations")
def get_all_conversations(user_id: str): 
    # TODO: Fetch conversations from Snowflake DB for the given user_id
    # SQL: SELECT id, title, updated_at FROM CONVERSATIONS 
    #      WHERE user_id = {user_id} ORDER BY updated_at DESC
    # For now, return a mock list:
    return [
        {"id": "1", "title": "Healthy Pasta Tips", "updated_at": "2023-10-27T10:00:00Z"},
        {"id": "2", "title": "Vegan Meal Prep", "updated_at": "2023-10-26T14:30:00Z"}
    ]


@router.get("/conversations/{conversation_id}/messages")
def get_messages(conversation_id: str):
    # TODO: Execute query in Snowflake...
    # This query fetches all past messages for the sidebar click
    # query = """
    # SELECT role, content, created_at 
    # FROM MESSAGES 
    # WHERE conversation_id = %s 
    # ORDER BY created_at ASC
    # """

    # For now, return a mock list:
    import random
    random_id = random.randint(1000, 9999)
    messages_list = [
        {"role": "user", "content": "This is a mocked conversation", "created_at": "2023-10-27T10:01:00Z"},
        {"role": "ai", "content": f"With {random_id} as an identifier", "created_at": "2023-10-27T10:02:00Z"},
    ]
    return messages_list if conversation_id <='2' else []


@router.post("/send")
def handle_chat(payload: dict): # TODO: Define payload model
    msg = payload.get("message")
    conv_id = payload.get("conversation_id")
    
    if not conv_id:
        # 1. Create new row in CONVERSATIONS table
        # 2. Assign the new ID to conv_id
        pass

    # 3. Save User message to MESSAGES table
    # 4. Get AI response
    # 5. Save AI response to MESSAGES table

    ai_resp = f"Mocked AI response to '{msg}' in conversation {conv_id}"
    
    return {"message": ai_resp, "conversation_id": conv_id}