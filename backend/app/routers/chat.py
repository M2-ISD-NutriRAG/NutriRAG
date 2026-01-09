import hashlib
import uuid
import json
import asyncio
from fastapi import APIRouter, HTTPException, Header, Request, Depends
from fastapi.responses import StreamingResponse
from app.services.api_agent import CortexAgentClient
from app.services.conversation_manager import ConversationManager
from app.utils.recipe_metadata_utils import (
    extract_metadata_from_event_stream,
    get_recipe_id_from_reference,
)

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

    # Conversation manager for context and recipe resolution
    conv_manager = ConversationManager(db)

    # Try to resolve references like "the third recipe" or
    # name-based references like "the breakfast hurry" using
    # stored recipes (IDs and optional names)
    recent_recipes = conv_manager.get_recent_recipes_for_reference(conv_id)
    resolved_recipe_id = get_recipe_id_from_reference(
        message_text, recent_recipes
    )

    resolution_hint = ""
    if resolved_recipe_id is not None:
        resolution_hint = (
            "RESOLVED_RECIPE_REFERENCE:\n"
            f"The user is referring to recipe with ID {resolved_recipe_id}. "
            "This ID comes from the most recent search results listed above.\n"
            "You MUST NOT call the search tool again just to rediscover this recipe. "
            "Instead, call the get_recipe_by_id tool with this recipe_id and use the returned recipe object for any detail or transform operations.\n\n"
        )

    # Get conversation context and AI response
    context = conv_manager.get_conversation_context(conv_id)

    # Prepare message with context and optional resolution hint
    full_message_parts = []
    if context:
        full_message_parts.append(context)
    if resolution_hint:
        full_message_parts.append(resolution_hint)
    full_message_parts.append(message_text)
    full_message = "".join(full_message_parts)

    try:
        # Initialize CortexAgentClient and get response
        agent_client = CortexAgentClient(snowflake_client=db)
        response = agent_client.call_agent(full_message)

        # Process the streaming response to get the complete content
        ai_response_content = ""
        current_event = None

        for line in response.iter_lines(decode_unicode=True):
            if line.strip() == "":
                continue

            if line.startswith("event: response.text.delta"):
                current_event = "response.text.delta"
                continue
            elif line.startswith("event: response.text"):
                current_event = "response.text"
                continue
            elif line.startswith("event: metadata"):
                current_event = "metadata"
                continue
            elif line.startswith("event: done"):
                break
            elif line.startswith("data: "):
                try:
                    data = json.loads(line[6:])

                    # Handle metadata events
                    if (
                        current_event == "metadata"
                        and "role" in data
                        and "message_id" in data
                    ):
                        thread_id = data.get("thread_id", 0)
                        message_id = data["message_id"]
                        role = data["role"]
                        conv_manager.store_thread_metadata(
                            conv_id, role, thread_id, message_id
                        )

                    # Handle text deltas
                    elif (
                        current_event == "response.text.delta"
                        and "text" in data
                    ):
                        ai_response_content += data["text"]
                    # Handle complete text response
                    elif current_event == "response.text" and "content" in data:
                        for content_item in data["content"]:
                            if (
                                content_item.get("type") == "text"
                                and "text" in content_item
                            ):
                                if (
                                    not ai_response_content
                                ):  # Only use if no delta content
                                    ai_response_content = content_item["text"]

                except json.JSONDecodeError:
                    continue

        ai_response = (
            ai_response_content.strip()
            or "I apologize, but I couldn't generate a response."
        )

    except Exception as e:
        ai_response = f"I apologize, but I encountered an error: {str(e)}"

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

    # Store the user's message in the conversation history (like non-streaming endpoint)
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
        collected_events = []  # Track events for metadata extraction

        try:
            # Send initial status
            yield f"data: {json.dumps({'type': 'conversation_id', 'conversation_id': conv_id})}\n\n"
            await asyncio.sleep(0)  # Force immediate yield

            # Send thinking status to start streaming immediately
            yield f"data: {json.dumps({'type': 'thinking', 'status': 'started', 'message': 'Processing your request...'})}\n\n"
            await asyncio.sleep(0)  # Force immediate yield

            # Conversation manager for context and recipe resolution
            conv_manager = ConversationManager(db)

            # Try to resolve references like "the third recipe" or
            # name-based references like "the breakfast hurry" using
            # stored recipes (IDs and optional names)
            recent_recipes = conv_manager.get_recent_recipes_for_reference(conv_id)
            resolved_recipe_id = get_recipe_id_from_reference(
                message_text, recent_recipes
            )

            resolution_hint = ""
            if resolved_recipe_id is not None:
                # Build a short, explicit hint for the agent to avoid re-search
                resolution_hint = (
                    "RESOLVED_RECIPE_REFERENCE:\n"
                    f"The user is referring to recipe with ID {resolved_recipe_id}. "
                    "This ID comes from the most recent search results listed above.\n"
                    "You MUST NOT call the search tool again just to rediscover this recipe. "
                    "Instead, call the get_recipe_by_id tool with this recipe_id and use the returned recipe object for any detail or transform operations.\n\n"
                )

            # Get conversation context for the agent (includes previous recipes)
            context = conv_manager.get_conversation_context(conv_id)

            # Prepare message with context and optional resolution hint
            full_message_parts = []
            if context:
                full_message_parts.append(context)
            if resolution_hint:
                full_message_parts.append(resolution_hint)
            full_message_parts.append(message_text)
            full_message = "".join(full_message_parts)

            # Initialize CortexAgentClient
            agent_client = CortexAgentClient(snowflake_client=db)

            # Get streaming response from CortexAgent
            response = agent_client.call_agent(full_message)
            current_event = None

            for line in response.iter_lines(decode_unicode=True):
                if line.strip() == "":
                    continue

                # Parse Server-Sent Events format - capture all event types
                if line.startswith("event: response.status"):
                    current_event = "response.status"
                    continue
                elif line.startswith("event: response.thinking.delta"):
                    current_event = "response.thinking.delta"
                    continue
                elif line.startswith("event: response.thinking"):
                    current_event = "response.thinking"
                    continue
                elif line.startswith("event: response.tool_result"):
                    current_event = "response.tool_result"
                    continue
                elif line.startswith("event: response.tool_result.status"):
                    current_event = "response.tool_result.status"
                    continue
                elif line.startswith("event: response.tool_use"):
                    current_event = "response.tool_use"
                    continue
                elif line.startswith("event: response.text.delta"):
                    current_event = "response.text.delta"
                    continue
                elif line.startswith("event: response.text"):
                    current_event = "response.text"
                    continue
                elif line.startswith("event: metadata"):
                    current_event = "metadata"
                    continue
                elif line.startswith("event: done"):
                    break  # End of stream
                elif line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])  # Remove "data: " prefix

                        # Handle tool result status
                        if (
                            current_event == "response.tool_result.status"
                            and "message" in data
                            and "status" in data
                        ):
                            yield f"data: {json.dumps({'type': 'tool_status', 'event': current_event, 'status': data['status'], 'message': data['message'], 'tool_type': data.get('tool_type'), 'tool_use_id': data.get('tool_use_id')})}\n\n"

                        # Handle tool results (the actual output from tools like search)
                        elif (
                            current_event == "response.tool_result"
                            and "content" in data
                        ):
                            # Track tool results for metadata extraction
                            collected_events.append({
                                'type': 'tool_result',
                                'tool_name': data.get('tool_name'),
                                'content': data.get('content'),
                                'tool_use_id': data.get('tool_use_id')
                            })

                        # Handle tool usage
                        elif (
                            current_event == "response.tool_use"
                            and "name" in data
                            and "input" in data
                        ):
                            # Track tool use events for metadata
                            collected_events.append({
                                'type': 'tool_use',
                                'tool_name': data['name'],
                                'tool_input': data['input'],
                                'tool_use_id': data.get('tool_use_id')
                            })

                            yield f"data: {json.dumps({'type': 'tool_use', 'event': current_event, 'tool_name': data['name'], 'tool_input': data['input'], 'tool_use_id': data.get('tool_use_id'), 'client_side_execute': data.get('client_side_execute'), 'content_index': data.get('content_index')})}\n\n"

                        # Handle thinking/status updates (both delta and complete)
                        elif (
                            current_event
                            in [
                                "response.status",
                                "response.thinking.delta",
                                "response.thinking",
                            ]
                            and "status" in data
                            and "message" in data
                        ):
                            yield f"data: {json.dumps({'type': 'thinking', 'event': current_event, 'status': data['status'], 'message': data['message']})}\n\n"

                        # Handle metadata events (thread/message IDs)
                        elif (
                            current_event == "metadata"
                            and "role" in data
                            and "message_id" in data
                        ):
                            # Store thread metadata for conversation continuity
                            # Note: thread_id may be available in some metadata events
                            thread_id = data.get(
                                "thread_id", 0
                            )  # Default to 0 if not provided
                            message_id = data["message_id"]
                            role = data["role"]

                            conv_manager.store_thread_metadata(
                                conv_id, role, thread_id, message_id
                            )

                        # Handle text deltas (incremental content)
                        elif (
                            current_event == "response.text.delta"
                            and "text" in data
                            and "content_index" in data
                        ):
                            text_chunk = data["text"]
                            ai_response_content += text_chunk
                            yield f"data: {json.dumps({'type': 'text_delta', 'event': current_event, 'text': text_chunk, 'content_index': data.get('content_index')})}\n\n"
                            await asyncio.sleep(0)  # Force immediate yield

                        # Handle complete text response
                        elif (
                            current_event == "response.text"
                            and "content" in data
                            and isinstance(data["content"], list)
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
                                        yield f"data: {json.dumps({'type': 'complete_response', 'event': current_event, 'text': final_content})}\n\n"

                    except json.JSONDecodeError:
                        # Skip malformed JSON lines
                        continue

            # Save AI response to database with metadata
            if ai_response_content.strip():
                # Extract recipe metadata from collected events
                metadata = extract_metadata_from_event_stream(collected_events)
                
                if metadata:
                    # Store message with metadata and use TO_VARIANT to convert the JSON string to VARIANT
                    metadata_json = json.dumps(metadata)
                    db.execute(
                        """
                        INSERT INTO MESSAGES (conversation_id, role, content, metadata)
                        SELECT %s, %s, %s, PARSE_JSON(%s)
                        """,
                        params=(conv_id, "assistant", ai_response_content.strip(), metadata_json),
                    )
                else:
                    db.execute(
                        """
                        INSERT INTO MESSAGES (conversation_id, role, content)
                        VALUES (%s, %s, %s)
                        """,
                        params=(conv_id, "assistant", ai_response_content.strip()),
                    )

            # Send completion signal
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            await asyncio.sleep(0)  # Force immediate yield

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
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
    )
