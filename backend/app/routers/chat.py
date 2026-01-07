import hashlib
import uuid
import json
from fastapi import APIRouter, HTTPException, Header, Request, Depends
from fastapi.responses import StreamingResponse
from shared.snowflake.client import SnowflakeClient
from app.services.api_agent import CortexAgentClient

# from app.models.auth import StartAuthRequest
router = APIRouter()


def get_db(
    request: Request,
):  # Dependency to get SnowflakeClient, from app main state
    return request.app.state.snowflake_client


def get_current_user(authorization: str = Header(None), db=Depends(get_db)):
    # 1. Check if the header exists
    if not authorization:
        raise HTTPException(
            status_code=401, detail="No Authorization header found"
        )

    # 2. Extract the actual token string
    try:
        token = authorization.split(" ")[1]
    except IndexError:
        raise HTTPException(status_code=401, detail="Invalid header format")

    token_hash = hashlib.sha256(token.encode()).hexdigest()
    # user = db.execute(f"SELECT username FROM USER_SESSIONS WHERE token_hash = '{token_hash}'", fetch="one")
    user = db.execute(
        f"SELECT username FROM USER_SESSIONS WHERE token_hash = %s",
        params=(token_hash,),
        fetch="one",
    )
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return user[0]


@router.get("/conversations")
def get_all_conversations(
    authorization: str = Header(None),
    db=Depends(get_db),
    username: str = Depends(get_current_user),
):
    res = db.execute(
        f""" SELECT id, title
                       FROM CONVERSATIONS
                       WHERE user_id = '{username}'
                       ORDER BY created_at DESC
                   """,
        fetch="all",
    )

    return [{"id": row[0], "title": row[1]} for row in res]


@router.get("/conversations/{conversation_id}/messages")
def get_messages(
    conversation_id: str,
    authorization: str = Header(None),
    db=Depends(get_db),
    username: str = Depends(get_current_user),
):
    can_access = db.execute(
        f""" SELECT id
                   FROM CONVERSATIONS
                   WHERE id = '{conversation_id}' AND user_id = '{username}'
               """,
        fetch="one",
    )
    if not can_access:
        raise HTTPException(
            status_code=403, detail="Access denied to this conversation"
        )

    res = db.execute(
        f""" SELECT role, content, created_at
                       FROM MESSAGES
                       WHERE conversation_id = %s
                       ORDER BY created_at ASC
                   """,
        params=(conversation_id,),
        fetch="all",
    )

    messages_list = [
        {"role": row[0], "content": row[1], "created_at": row[2]} for row in res
    ]

    # For now, return a mock list:
    return messages_list


@router.post("/conversations")
def create_conversation(
    payload: dict,
    authorization: str = Header(None),
    db=Depends(get_db),
    username: str = Depends(get_current_user),
):
    """Create a new conversation for the user."""
    _ = username  # Just to ensure user is valid

    conv_id = str(uuid.uuid4())  # Generate a new conversation ID
    title = payload.get("title", "New Conversation")

    return {"id": conv_id, "title": title}


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    authorization: str = Header(None),
    db=Depends(get_db),
    username: str = Depends(get_current_user),
):
    """Delete a conversation and its messages."""
    can_access = db.execute(
        f""" SELECT id
                   FROM CONVERSATIONS
                   WHERE id = '{conversation_id}' AND user_id = '{username}'
               """,
        fetch="one",
    )
    if not can_access:
        raise HTTPException(
            status_code=403, detail="Access denied to this conversation"
        )
    db.execute(
        f""" DELETE FROM MESSAGES
                    WHERE conversation_id = %s
                """,
        params=(conversation_id,),
    )
    db.execute(
        f""" DELETE FROM CONVERSATIONS
                    WHERE id = %s
                """,
        params=(conversation_id,),
    )
    return {"ok": True}


@router.post("/send")
def handle_chat(
    payload: dict,
    authorization: str = Header(None),
    db=Depends(get_db),
    username: str = Depends(get_current_user),
):
    """Handle sending a message and getting AI response."""

    conv_id = payload.get("conversation_id")  # Might be null if it's a new chat
    message_text = payload.get("message")

    # If no conv_id, this is the FIRST message of a new chat
    if not conv_id:
        conv_id = str(uuid.uuid4())
        print("INSERT INTO CONVERSATIONS", conv_id, message_text)
        db.execute(
            f"""
            INSERT INTO CONVERSATIONS (id, user_id, title)
            VALUES (%s, %s, %s)
        """,
            params=(
                conv_id,
                username,
                (
                    " ".join(message_text[:27].split()[:-1])
                    if " " in message_text
                    else "New Conversation"
                )
                + "...",
            ),
        )

    db.execute(
        f"""
        INSERT INTO MESSAGES (conversation_id, role, content)
        VALUES (%s, %s, %s)
    """,
        params=(conv_id, "user", message_text),
    )

    # ... Get AI Response ...

    # HERE @Tiphaine

    import random

    random_id = random.randint(1000, 9999)
    ai_response = f"This is a mocked AI response with id {random_id}"

    # Add AI response to conversation history
    db.execute(
        f"""
        INSERT INTO MESSAGES (conversation_id, role, content)
        VALUES (%s, %s, %s)
    """,
        params=(conv_id, "assistant", ai_response),
    )

    return {"conversation_id": conv_id, "message": ai_response}


@router.post("/send-stream")
async def handle_chat_stream(
    payload: dict,
    authorization: str = Header(None),
    db=Depends(get_db),
    username: str = Depends(get_current_user),
):
    """Handle sending a message and getting streaming AI response with thinking status."""

    conv_id = payload.get("conversation_id")
    message_text = payload.get("message")

    # If no conv_id, this is the FIRST message of a new chat
    if not conv_id:
        conv_id = str(uuid.uuid4())
        db.execute(
            f"""
            INSERT INTO CONVERSATIONS (id, user_id, title)
            VALUES (%s, %s, %s)
        """,
            params=(
                conv_id,
                username,
                (
                    " ".join(message_text[:27].split()[:-1])
                    if " " in message_text
                    else "New Conversation"
                )
                + "...",
            ),
        )

    # Save user message
    db.execute(
        f"""
        INSERT INTO MESSAGES (conversation_id, role, content)
        VALUES (%s, %s, %s)
    """,
        params=(conv_id, "user", message_text),
    )

    async def generate_response():
        """Generator function for streaming response."""
        ai_response_content = ""

        try:
            # Send initial status
            yield f"data: {json.dumps({'type': 'conversation_id', 'conversation_id': conv_id})}\n\n"

            # Initialize CortexAgentClient
            agent_client = CortexAgentClient(snowflake_client=db)

            # Get streaming response from CortexAgent
            response = agent_client.call_agent(message_text)

            for line in response.iter_lines(decode_unicode=True):
                if line.strip() == "":
                    continue

                # Parse Server-Sent Events format
                if line.startswith("event: response.status"):
                    continue  # Skip event line, data is on next line
                elif line.startswith("event: response.text.delta"):
                    continue  # Skip event line, data is on next line
                elif line.startswith("event: response"):
                    continue  # Skip event line, data is on next line
                elif line.startswith("event: done"):
                    break  # End of stream
                elif line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])  # Remove "data: " prefix

                        # Handle thinking/status updates
                        if "status" in data and "message" in data:
                            yield f"data: {json.dumps({'type': 'thinking', 'status': data['status'], 'message': data['message']})}\n\n"

                        # Handle text deltas (incremental content)
                        elif "text" in data and "content_index" in data:
                            text_chunk = data["text"]
                            ai_response_content += text_chunk
                            yield f"data: {json.dumps({'type': 'text_delta', 'text': text_chunk})}\n\n"

                        # Handle final response
                        elif "content" in data and isinstance(
                            data["content"], list
                        ):
                            for content_item in data["content"]:
                                if (
                                    content_item.get("type") == "text"
                                    and "text" in content_item
                                ):
                                    # This is the final complete response
                                    final_content = content_item["text"]
                                    if (
                                        final_content
                                        and not ai_response_content
                                    ):
                                        ai_response_content = final_content
                                        yield f"data: {json.dumps({'type': 'complete_response', 'text': final_content})}\n\n"

                    except json.JSONDecodeError:
                        # Skip malformed JSON lines
                        continue

            # Save AI response to database
            if ai_response_content.strip():
                db.execute(
                    f"""
                    INSERT INTO MESSAGES (conversation_id, role, content)
                    VALUES (%s, %s, %s)
                """,
                    params=(conv_id, "assistant", ai_response_content.strip()),
                )

            # Send completion signal
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            # Send error to client
            error_msg = f"Error getting AI response: {str(e)}"
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"

            # Save error response to database
            db.execute(
                f"""
                INSERT INTO MESSAGES (conversation_id, role, content)
                VALUES (%s, %s, %s)
            """,
                params=(
                    conv_id,
                    "assistant",
                    f"Sorry, I encountered an error: {str(e)}",
                ),
            )

    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
    )
