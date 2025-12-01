# Show/Hide Non-Matching Tables Feature

## Overview
Added a new toggle option in column search mode to show or hide tables that don't have matching columns.

## Changes Made

### 1. New Configuration Option
- Added `show_non_matching_tables` boolean flag to `DBBrowserApp.__init__()`
- Default: `True` (shows all tables including non-matching)

### 2. New Key Binding
- Added `Binding("h", "toggle_non_matching", "Show/Hide Non-Matching")`
- Only active in column search mode

### 3. New Action Method
- `action_toggle_non_matching()` method to toggle the flag
- Shows informative notifications
- Clears UI cache and refreshes display

### 4. Updated Column Search Logic
- Modified table display loop to respect `show_non_matching_tables` flag
- Tables with matches: Always shown with match count
- Tables without matches: Only shown when flag is `True`
- Non-matching tables displayed with "·" prefix for visual distinction

### 5. Enhanced Info Display
- Shows different messages based on toggle state:
  - **All tables**: `Tables (6 total, 3 with matches, 3 matching columns total)`
  - **Matches only**: `Tables (3 with matches, 3 matching columns total) [H: toggle non-matching]`

### 6. Updated Help System
- Added "H: show/hide non-matching tables" to help text in column search mode
- Updated search mode toggle notification to mention H key

## User Experience

### Default Behavior (show_non_matching_tables=True)
```
Tables (6 total, 3 with matches, 3 matching columns total)
├── USERS — 1 matching columns
├── · ORDERS — no matching columns  
├── PRODUCTS — 1 matching columns
├── CUSTOMERS — 1 matching columns
├── · INVOICES — no matching columns
└── · OHHST — no matching columns
```

### Hidden Non-Matching (show_non_matching_tables=False)
```
Tables (3 with matches, 3 matching columns total) [H: toggle non-matching]
├── USERS — 1 matching columns
├── PRODUCTS — 1 matching columns
└── CUSTOMERS — 1 matching columns
```

## Key Benefits

1. **Reduced Clutter**: Users can focus only on relevant tables when searching
2. **Better Performance**: Fewer tables to render and navigate
3. **Flexible Workflow**: Easy toggle between comprehensive vs focused views
4. **Visual Clarity**: Clear distinction between matching and non-matching tables
5. **Contextual Help**: Info text shows current state and how to change it

## Usage

1. Press `Tab` to switch to column search mode
2. Type search query (e.g., "name")
3. Press `H` to toggle show/hide non-matching tables
4. Press `H` again to restore all tables

## Technical Details

- **State Management**: Toggle stored in `show_non_matching_tables` instance variable
- **Cache Invalidation**: Calls `_clear_ui_cache()` to force refresh
- **UI Update**: Calls `update_tables_display()` to re-render
- **Performance**: Uses pre-computed search data for fast filtering
- **Visual Design**: Uses "·" prefix for non-matching items (consistent with column dimming)

## Testing

- All existing tests pass
- New functionality tested with mock data
- Toggle behavior verified in both search modes
- Edge cases handled (table mode, empty queries, etc.)

## Backward Compatibility

- Fully backward compatible
- Default behavior shows all tables (existing behavior)
- No breaking changes to existing functionality
- Optional feature that users can ignore if not needed