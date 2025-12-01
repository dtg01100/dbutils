# DB Browser - Qt Experimental Branch

## 🚀 Overview

This is an **experimental Qt-based GUI version** of the DB Browser utility, providing a modern graphical interface for database schema browsing with advanced features including streaming search, visualizations, and enhanced user experience.

## 🎯 Key Features

### **🖥️ Modern Qt Interface**
- **Rich Table Views**: Sortable, filterable tables and columns
- **Advanced Search**: Streaming search with real-time results
- **Multi-Panel Layout**: Resizable tables and columns panels
- **Visual Indicators**: Progress bars, status icons, animations
- **Context Menus**: Right-click actions and shortcuts

### **🔍 Streaming Search**
- **Real-Time Results**: See matches as they're found
- **Progressive Display**: Results appear incrementally
- **Relevance Scoring**: Best matches shown first
- **Search History**: Previous searches easily accessible
- **Advanced Filters**: Schema, table type, and custom filters

### **📊 Enhanced Data Display**
- **Rich Formatting**: Syntax highlighting, icons, and visual indicators
- **Interactive Tables**: Click to select, double-click for details
- **Column Statistics**: Type information, nullability, descriptions
- **Schema Organization**: Grouped by schema with expand/collapse

### **⚙️ Advanced Configuration**
- **Smart Interface Detection**: Automatically chooses Qt/TUI/CLI
- **User Preferences**: Remember interface choice and settings
- **Customizable Layouts**: Save and restore panel arrangements
- **Theme Support**: Light/dark themes with system integration

## 🏗️ Architecture

```
src/dbutils/
├── gui/                          # Qt GUI implementation
│   ├── qt_app.py               # Main Qt application
│   ├── widgets/                 # Custom Qt widgets
│   │   └── enhanced_widgets.py # Enhanced UI components
│   └── resources/               # Icons, themes, assets
├── tui/                          # Textual TUI (existing)
│   └── db_browser.py          # Terminal-based interface
├── main_launcher.py              # Smart interface selector
└── __init__.py                 # Updated entry points
```

## 🚀 Installation

### **Option 1: Qt GUI (Recommended)**
```bash
# Install Qt dependencies
pip install -r requirements-qt.txt

# Run with auto-detection
python -m dbutils

# Force Qt mode
python -m dbutils --force-gui
```

### **Option 2: Textual TUI (Existing)**
```bash
# Install TUI dependencies
pip install textual rich

# Run with auto-detection
python -m dbutils

# Force TUI mode
python -m dbutils --force-tui
```

### **Option 3: CLI Interface**
```bash
# CLI mode for scripting
python -m dbutils --force-cli --search "user"
```

## 🎮 Usage Examples

### **Qt GUI Mode**
```bash
# Launch with auto-detection
python -m dbutils

# Force Qt GUI
python -m dbutils --force-gui

# With schema filter
python -m dbutils --force-gui --schema DACDATA

# With mock data for testing
python -m dbutils --force-gui --mock

# Disable streaming search
python -m dbutils --force-gui --no-streaming
```

### **Interface Selection**
```bash
# Show environment detection info
python -m dbutils --info

# Auto-detects best interface based on:
# - Display availability (X11/Wayland/Windows/macOS)
# - SSH session detection
# - User preferences
# - Library availability
```

## 🎨 Qt Interface Features

### **Main Window**
- **Splitter Layout**: Resizable tables and columns panels
- **Menu Bar**: File, View, Help menus with keyboard shortcuts
- **Status Bar**: Progress indicators, status messages, and statistics
- **Search Panel**: Advanced search with autocomplete and filters

### **Tables Panel**
- **Enhanced Table View**: Sortable columns, visual indicators
- **Match Types**: Icons for exact (🎯), prefix (📍), fuzzy (🔍) matches
- **Context Menu**: Right-click for table actions
- **Selection**: Single-click to show columns, double-click for details

### **Columns Panel**
- **Rich Column Display**: Type information with formatting
- **Nullability Indicators**: Visual Y/N indicators
- **Length/Scale**: Precise data type information
- **Descriptions**: Full column descriptions with word wrap

### **Search System**
- **Streaming Results**: Real-time result display
- **Search Modes**: Table search vs Column search
- **Advanced Filters**: Schema, table type, custom filters
- **Search History**: Dropdown with previous searches
- **Keyboard Shortcuts**: Quick access to common actions

## 🔧 Advanced Configuration

### **Environment Detection**
The smart launcher automatically detects:

1. **Display Environment**
   - X11 (Linux desktop)
   - Wayland (modern Linux)
   - Windows (Windows desktop)
   - macOS (macOS desktop)
   - SSH (remote terminal)
   - Headless (no display)

2. **Library Availability**
   - PySide6/PyQt6 for Qt GUI
   - Textual for terminal TUI
   - Rich for CLI output

3. **User Preferences**
   - Saved interface choice
   - Last used settings
   - Custom configurations

### **Preference System**
```json
~/.config/dbutils/config.json
{
    "preferred_interface": "qt",
    "last_used": "qt",
    "qt_settings": {
        "window_geometry": "1200x800+100+100",
        "splitter_sizes": [600, 600],
        "theme": "system"
    },
    "tui_settings": {
        "streaming_enabled": true,
        "show_non_matching": true
    }
}
```

## 🚦 Development

### **Building Qt Interface**
```bash
# Install development dependencies
pip install -r requirements-qt.txt
pip install pytest-qt black mypy

# Run tests
pytest tests/test_qt_browser.py

# Code formatting
black src/dbutils/gui/

# Type checking
mypy src/dbutils/gui/
```

### **Testing Strategy**
- **Unit Tests**: Widget behavior and model logic
- **Integration Tests**: Database connectivity and search
- **GUI Tests**: User interactions and visual behavior
- **Performance Tests**: Search speed and memory usage

## 🔄 Migration from TUI

### **For Existing Users**
1. **Automatic Detection**: Launcher chooses Qt if display available
2. **Manual Override**: Use `--force-tui` to keep TUI
3. **Gradual Transition**: Try Qt GUI, fall back to TUI if needed
4. **Feature Parity**: All TUI features available in Qt

### **Feature Mapping**
| TUI Feature | Qt Equivalent | Enhancement |
|-------------|----------------|------------|
| Table Search | Search Panel | Streaming, history, filters |
| Column Search | Column Search Panel | Rich formatting, sorting |
| Keyboard Nav | Mouse + Keyboard | Click, drag-drop, shortcuts |
| Status Bar | Enhanced Status Bar | Progress bars, visual indicators |
| Help System | Menu Bar + Help Menu | Organized, searchable help |

## 🎯 Performance

### **Qt Advantages**
- **Rich Interactions**: Mouse, drag-drop, multi-select
- **Visual Feedback**: Animations, progress bars, status icons
- **Advanced Features**: Complex layouts, custom widgets
- **Integration**: System clipboard, file dialogs, notifications
- **Accessibility**: Screen reader support, keyboard navigation

### **Optimizations**
- **Lazy Loading**: Load data on-demand
- **Streaming Search**: Results appear as found
- **Memory Management**: Efficient models and caching
- **Background Processing**: Non-blocking search operations
- **Smart Updates**: Only refresh changed components

## 🔮 Future Roadmap

### **Phase 1: Core Qt Features** (Current)
- ✅ Basic Qt interface
- ✅ Streaming search
- ✅ Enhanced table/column display
- ✅ Smart launcher

### **Phase 2: Advanced Features** (Next)
- 🔄 Visual schema diagrams
- 🔄 Query builder interface
- 🔄 Export/import wizards
- 🔄 Plugin architecture
- 🔄 Multi-window support

### **Phase 3: Enterprise Features** (Future)
- 🔮 Database connection manager
- 🔮 Query execution interface
- 🔮 Result visualization charts
- 🔮 Collaboration features
- 🔮 Advanced scripting interface

## 🐛 Known Issues

### **Current Limitations**
- **Experimental**: Qt interface is experimental and may have bugs
- **Feature Parity**: Not all TUI features implemented yet
- **Performance**: May be slower than TUI for very large datasets
- **Memory**: Qt applications use more memory than TUI

### **Workarounds**
- Use `--force-tui` if Qt interface has issues
- Use `--no-streaming` if search performance is poor
- Use mock data (`--mock`) for testing without database

## 📞 Support

### **Getting Help**
```bash
# Show all options
python -m dbutils --help

# Environment detection info
python -m dbutils --info

# Force specific interface
python -m dbutils --force-gui    # Qt GUI
python -m dbutils --force-tui    # Textual TUI
python -m dbutils --force-cli    # CLI
```

### **Reporting Issues**
When reporting issues with the Qt interface:
1. **Environment**: Use `--info` to show detection results
2. **Interface**: Specify if using Qt, TUI, or CLI
3. **Reproduction**: Steps to reproduce the issue
4. **Expected**: What you expected to happen
5. **Actual**: What actually happened
6. **System**: OS, Python version, Qt library version

---

**Note**: This Qt implementation is experimental and under active development. The Textual TUI remains the stable, production-ready interface for critical use cases.