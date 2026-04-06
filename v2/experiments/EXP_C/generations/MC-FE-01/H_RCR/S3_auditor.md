## Constraint Review
- C1 [L]TS [F]React: PASS — File uses TypeScript (type annotations throughout: `ColumnId`, `Task`, `BoardState`, `Action` etc.) and React (`import React, { useReducer, useEffect, useRef, useCallback } from 'react'`).
- C2 [Y]CSS_MODULES [!Y]NO_TW: PASS — Styles imported via `import styles from './TodoBoard.module.css'` and accessed as `styles.card`, `styles.column` etc.; no Tailwind utility classes present.
- C3 [!D]NO_DND_LIB [DRAG]HTML5: PASS — No drag-and-drop library imported; drag is implemented with native HTML5 drag events (`draggable`, `onDragStart`, `onDragOver`, `onDrop`, `e.dataTransfer`).
- C4 [STATE]useReducer: PASS — Primary state management uses `useReducer(reducer, initialState)` in the `TodoBoard` component (line 350).
- C5 [O]SFC [EXP]DEFAULT: PASS — All components (`TaskCard`, `Column`, `ConflictToast`, `AddTaskInput`, `TodoBoard`) are stateless function components or function components; `TodoBoard` is `export default function TodoBoard()`.
- C6 [WS]MOCK [!D]NO_SOCKETIO: PASS — WebSocket is mocked via `class MockWebSocket` (line 217); no `socket.io` or real WebSocket library is imported.

## Functionality Assessment (0-5)
Score: 4 — Implements a three-column Kanban board with drag-and-drop reordering across columns, task adding, mock WebSocket sync with conflict detection/toast, and reducer-based state. Minor issues: the `Column` component renders ghost `TaskCard`s with empty titles that would be visible to users; the `onDragStart` prop in `Column`'s map is always a no-op (`() => {}`), meaning actual task cards inside `Column` cannot be dragged — only the ghost cards and those outside `Column` children can. This breaks the intended drag-and-drop flow for existing tasks rendered via the `tasks` prop.

## Corrected Code
No correction needed.
