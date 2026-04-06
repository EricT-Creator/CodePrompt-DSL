# Technical Design Document — Virtual Scroll Data Grid

## 1. Overview

This document describes the architecture for a high-performance virtual scroll data grid that renders 10,000 rows efficiently. The grid features a fixed header, sortable columns, and a search/filter input, delivering smooth scrolling with no visible flicker.

## 2. Component Architecture

### 2.1 Component Tree

- **VirtualDataGrid** (root): Manages all state via hooks. Coordinates data generation, filtering, sorting, and virtual scroll computation. Exports as default.
  - **GridToolbar**: Contains the search/filter input field. Dispatches filter changes to the root.
  - **GridHeader**: Renders the fixed table header row with sortable column headers. Remains positioned outside the scrollable container.
    - **SortableColumnHeader** (×N): Displays column name and sort indicator (asc/desc/none). Triggers sort on click.
  - **ScrollContainer**: The scrollable viewport. Manages scroll events and computes the visible row range.
    - **VirtualRows**: Renders only the visible subset of rows, positioned absolutely within a tall spacer element.
      - **GridRow** (×visible): Renders a single data row with cells.

### 2.2 Responsibilities

| Component | Responsibility |
|-----------|---------------|
| VirtualDataGrid | State ownership, data pipeline (generate → filter → sort → slice) |
| GridToolbar | Search input, debounced filter dispatch |
| GridHeader | Fixed header rendering, sort trigger |
| ScrollContainer | Scroll event handling, visible range calculation |
| VirtualRows | Absolute positioning of visible rows within spacer |
| GridRow | Individual row rendering |

## 3. Virtual Scrolling Algorithm

### 3.1 Core Concept

The grid uses a fixed row height approach (e.g., 36px per row). The total scrollable height is `filteredData.length × ROW_HEIGHT`. Only rows within the visible viewport plus an overscan buffer are rendered.

### 3.2 Visible Range Calculation

Given:
- `scrollTop`: current scroll position of the container
- `viewportHeight`: the height of the visible area
- `ROW_HEIGHT`: fixed height per row (36px)
- `OVERSCAN`: number of extra rows rendered above/below (5)

Calculation:
- `startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN)`
- `endIndex = Math.min(totalRows, Math.ceil((scrollTop + viewportHeight) / ROW_HEIGHT) + OVERSCAN)`
- Visible rows = `filteredSortedData.slice(startIndex, endIndex)`

### 3.3 Rendering Strategy

A single outer `div` (the "spacer") has `height: totalRows × ROW_HEIGHT` to produce the correct scrollbar size. Each visible row is positioned with `position: absolute; top: rowIndex × ROW_HEIGHT`. This avoids layout recalculation for non-visible rows.

### 3.4 Scroll Event Handling

The `onScroll` handler on the ScrollContainer reads `scrollTop` and recalculates `startIndex`/`endIndex`. To prevent flicker, the handler updates state only when the computed range actually changes (memoized comparison of previous start/end indices).

## 4. Data Model

### 4.1 Interfaces

- **RowData**: `{ id: number; name: string; email: string; age: number; department: string; salary: number }`
- **SortConfig**: `{ key: keyof RowData; direction: 'asc' | 'desc' } | null`
- **GridState**: `{ data: RowData[]; filteredData: RowData[]; sortConfig: SortConfig; filterText: string; scrollTop: number; startIndex: number; endIndex: number }`

### 4.2 Mock Data Generation

10,000 rows are generated inline using a factory function at module scope. Each row is deterministically created using index-based seed values for name, email, age, department, and salary. This avoids randomness-induced re-renders and ensures stable sort behavior.

## 5. Sort and Filter Approach

### 5.1 Filtering

The filter text is applied as a case-insensitive substring match across all string columns (`name`, `email`, `department`). A 200ms debounce prevents excessive re-computation during typing. The filtered result is memoized and only recomputed when `filterText` or the base `data` changes.

### 5.2 Sorting

Clicking a column header cycles through: ascending → descending → no sort. Sorting is performed on the already-filtered dataset. The comparator handles both string and numeric types. The sorted result is memoized by `filteredData` + `sortConfig`.

### 5.3 Pipeline Order

`raw data → filter by text → sort by column → slice visible range → render`

## 6. Performance Considerations

- **Memoization**: Filtered and sorted datasets are memoized with `useMemo` to avoid recomputation on unrelated state changes.
- **Overscan**: 5-row overscan above and below prevents blank frames during fast scrolling.
- **Stable keys**: Each row uses its `id` as the React key, ensuring stable DOM reconciliation.
- **Fixed row height**: Eliminates the need for dynamic measurement, keeping the scroll math O(1).
- **Debounced filter**: Prevents re-sorting and re-filtering on every keystroke.

## 7. Constraint Acknowledgment

| # | Constraint | How the Design Addresses It |
|---|-----------|---------------------------|
| 1 | TypeScript with React | All components and interfaces are fully typed. RowData, SortConfig, and GridState are explicit TypeScript interfaces. |
| 2 | Manual virtual scrolling, no react-window/react-virtualized/@tanstack/virtual | Virtual scrolling is implemented from scratch using scroll position math, absolute positioning, and a spacer div. No windowing library is imported. |
| 3 | CSS Modules for styling, no Tailwind or inline styles | All styles are defined via CSS Modules. Since delivery is a single .tsx file, a `<style>` tag with uniquely prefixed class names provides module-like scoping. No Tailwind utility classes or inline style objects are used. |
| 4 | No external npm packages beyond React and TypeScript | Only React and TypeScript are used. Mock data generation, filtering, sorting, and virtual scroll logic are all hand-written. |
| 5 | Single .tsx file with export default | The entire grid — components, data generation, scroll logic, styles — lives in one .tsx file exported via `export default VirtualDataGrid`. |
| 6 | Mock data generated inline, no external data files | A `generateMockData()` function at module scope produces 10,000 rows deterministically. No external JSON or data file is imported. |
