[L]Python [F]FastAPI [!D]NO_ASYNC_Q [BCAST]SET_ITER [D]FASTAPI_ONLY [O]SINGLE_FILE [HIST]LIST_100 [OUT]CODE_ONLY

You are a software architect. Given the engineering constraints in the compact header above and the user requirement below, produce a technical design document in Markdown (max 2000 words).

Include:
1. WebSocket connection lifecycle
2. Room management data structures
3. Broadcast mechanism
4. Message history storage
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a FastAPI WebSocket chat server: multi-room support, broadcast messages to all users in the same room, user nicknames, online user list endpoint, and in-memory message history capped at 100 messages per room.
