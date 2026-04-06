# Technical Design Document — Virtual Scroll Data Grid

## 1. Overview

A high-performance data grid rendering 10,000 rows through manual virtual scrolling. Features include a fixed header row, sortable columns, and a search/filter input — all built without external dependencies.

## 2. Component Architecture

### 2.1 `DataGrid` (root, export default)
- Initializes the 10,000-row mock dataset on mount.
- Manages sort state, filter text, and scroll offset.
- Composes `GridHeader`, `VirtualBody`, and `FilterBar`.

### 2.2 `FilterBar`
- A controlled text input.
- On change, updates the filter string in state; the filtered dataset is derived via `useMemo`.

### 2.3 `GridHeader`
- Renders the fixed header row with column labels.
- Each column header is clickable for sort toggling (ascending → descending → none).
- Positioned with `position: sticky; top: 0` inside the scroll container or rendered outside the scrollable area.

### 2.4 `VirtualBody`
- The scrollable container with a fixed viewport height.
- Contains an inner spacer `div` whose height equals `totalRows × ROW_HEIGHT`, creating a native scrollbar.
- Listens to `onScroll` to compute the visible window and renders only the rows within that window plus an overscan buffer.

### 2.5 `GridRow`
- A single table-like row rendering cell values.
- Receives absolute `top` positioning via inline style (translated from its index × ROW_HEIGHT).

## 3. Virtual Scrolling Algorithm

### Constants
- `ROW_HEIGHT` = 36 px (fixed).
- `VIEWPORT_HEIGHT` = container height (e.g., 600 px).
- `OVERSCAN` = 5 rows above and below the visible range.

### Visible Range Calculation

```
scrollTop = container.scrollTop
startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN)
endIndex = Math.min(totalRows - 1, Math.ceil((scrollTop + VIEWPORT_HEIGHT) / ROW_HEIGHT) + OVERSCAN)
visibleSlice = filteredSortedData.slice(startIndex, endIndex + 1)
```

### Rendering Strategy
- The outer container has `overflow-y: auto` and a fixed height.
- Inside, a spacer div has `height: totalRows * ROW_HEIGHT`.
- Each rendered row is `position: absolute; top: index * ROW_HEIGHT`.
- On scroll, only `startIndex` and `endIndex` are recalculated (via `onScroll` handler that sets state or ref). Using a `useRef` for `scrollTop` + `requestAnimationFrame` debounce avoids excessive re-renders and prevents flicker.

### Flicker Prevention
- Overscan buffer ensures rows are pre-rendered before entering the viewport.
- `will-change: transform` on the row container aids compositor-layer promotion.
- Row components are memoized (`React.memo`) with stable keys to avoid unnecessary DOM churn.

## 4. Data Model

### Interfaces

- **RowData**: `{ id: number; name: string; email: string; age: number; city: string; score: number }`
- **SortConfig**: `{ column: keyof RowData | null; direction: 'asc' | 'desc' | null }`
- **GridState**: `{ data: RowData[]; filter: string; sort: SortConfig; scrollTop: number }`

### Inline Mock Data
- Generated once via a factory function: `Array.from({ length: 10000 }, (_, i) => ({ id: i, name: \`User ${i}\`, ... }))`.
- Stored in a `useRef` to avoid regeneration on re-render.

## 5. Sort and Filter Approach

### Filtering
- `useMemo` derives `filteredData` from `data` + `filter` string.
- Filter checks each row's `name` and `email` fields with case-insensitive `includes`.

### Sorting
- `useMemo` derives `sortedData` from `filteredData` + `sort` config.
- For string columns: `localeCompare`.
- For numeric columns: arithmetic comparison.
- At least two columns (`name` and `score`) are sortable. Column header click cycles `asc → desc → null`.

### Pipeline
`rawData → filter → sort → virtualSlice → render`

Each stage is memoized so that scrolling alone (which only changes the visible slice) does not re-sort or re-filter.

## 6. Constraint Acknowledgment

| # | Constraint | Design Response |
|---|-----------|----------------|
| 1 | **TS + React** | All components are TypeScript React functional components. Interfaces are explicitly typed. |
| 2 | **Manual virtual scroll, no react-window** | Virtual scrolling is implemented from scratch using `scrollTop` math, a spacer div, and absolute-positioned rows. No `react-window`, `react-virtualized`, or similar library. |
| 3 | **CSS Modules, no Tailwind/inline** | All styling lives in co-located `.module.css` files. No Tailwind utility classes. Inline styles are used *only* for the dynamic `top` positioning of virtual rows (unavoidable for virtual scroll). |
| 4 | **No external deps** | Zero `import` statements referencing packages outside React and React-DOM. Mock data, sorting, and filtering are all hand-written. |
| 5 | **Single file, export default** | The entire grid — components, hooks, mock data generator, types — resides in a single `.tsx` file with `export default DataGrid`. The CSS Module is the only companion file. |
| 6 | **Inline mock data** | A factory function inside the file generates 10,000 rows at initialization. No JSON import, no fetch call. |
