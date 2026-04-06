You are a software architect. Given the engineering constraints and user requirement below, produce a technical design document in Markdown (max 2000 words).

Engineering Constraints:
Python + FastAPI. No asyncio.Queue for broadcast, use set iteration. fastapi + uvicorn only. Single file. In-memory list, max 100 msgs per room. Code only.

Include:
1. WebSocket connection lifecycle
2. Room management data structures
3. Broadcast mechanism
4. Message history storage
5. Constraint acknowledgment section: For EACH constraint, state how the design addresses it

Do NOT write code. Output the design document only.

User Requirement:
Build a FastAPI WebSocket chat server: multi-room support, broadcast messages to all users in the same room, user nicknames, online user list endpoint, and in-memory message history capped at 100 messages per room.
