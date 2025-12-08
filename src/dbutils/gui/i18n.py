#!/usr/bin/env python3
"""
Internationalization (i18n) Module

Internationalization support for the database browser application.
This module addresses the lack of multi-language support by providing:
- String externalization
- Language selection
- Translation management
- Locale-aware formatting
- RTL language support

Features:
- Translation management system
- Language detection and selection
- Locale-aware date/time and number formatting
- Right-to-left language support
- Translation file management
"""

from __future__ import annotations

import json
import locale
import threading
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class Language(Enum):
    """Supported languages."""

    ENGLISH = auto()
    SPANISH = auto()
    FRENCH = auto()
    GERMAN = auto()
    CHINESE = auto()
    JAPANESE = auto()
    ARABIC = auto()
    RUSSIAN = auto()


@dataclass
class Translation:
    """Translation data for a specific language."""

    language: Language
    translations: Dict[str, str]
    locale: str
    is_rtl: bool = False


@dataclass
class LocaleSettings:
    """Locale-specific settings."""

    date_format: str
    time_format: str
    number_format: Dict[str, Any]
    currency_symbol: str
    decimal_separator: str
    thousands_separator: str


class I18nManager:
    """Internationalization management for the database browser."""

    def __init__(self):
        self._current_language: Language = Language.ENGLISH
        self._translations: Dict[Language, Translation] = {}
        self._locale_settings: Dict[Language, LocaleSettings] = {}
        self._fallback_language: Language = Language.ENGLISH
        self._translation_dir: Path = Path(__file__).parent / "translations"
        self._lock = threading.RLock()

        # Initialize with default translations
        self._initialize_default_translations()
        self._initialize_locale_settings()

    def _initialize_default_translations(self):
        """Initialize default English translations."""
        # Create translations directory if it doesn't exist
        self._translation_dir.mkdir(exist_ok=True)

        # Load or create English translations
        english_file = self._translation_dir / "en.json"
        if english_file.exists():
            self._load_translations(Language.ENGLISH, english_file)
        else:
            # Create default English translations
            default_translations = {
                # Common UI elements
                "search": "Search",
                "tables": "Tables",
                "columns": "Columns",
                "settings": "Settings",
                "help": "Help",
                "about": "About",
                "exit": "Exit",
                "cancel": "Cancel",
                "ok": "OK",
                "save": "Save",
                "load": "Load",
                "refresh": "Refresh",
                "clear": "Clear",
                "filter": "Filter",
                "sort": "Sort",
                "export": "Export",
                "import": "Import",
                # Database-specific terms
                "database": "Database",
                "schema": "Schema",
                "table": "Table",
                "column": "Column",
                "row": "Row",
                "query": "Query",
                "connection": "Connection",
                "provider": "Provider",
                "driver": "Driver",
                # Messages
                "loading": "Loading...",
                "error": "Error",
                "success": "Success",
                "warning": "Warning",
                "info": "Information",
                "no_results": "No results found",
                "confirm_delete": "Are you sure you want to delete this?",
                "operation_completed": "Operation completed successfully",
                # Accessibility
                "accessibility": "Accessibility",
                "high_contrast": "High Contrast",
                "screen_reader": "Screen Reader",
                "keyboard_navigation": "Keyboard Navigation",
                # Performance
                "performance": "Performance",
                "memory_usage": "Memory Usage",
                "optimize": "Optimize",
                # Theming
                "theme": "Theme",
                "light_theme": "Light Theme",
                "dark_theme": "Dark Theme",
                "system_theme": "System Theme",
            }

            self._translations[Language.ENGLISH] = Translation(
                language=Language.ENGLISH, translations=default_translations, locale="en_US", is_rtl=False
            )

            # Save default translations
            self.save_translations(Language.ENGLISH)

    def _initialize_locale_settings(self):
        """Initialize locale-specific settings."""
        # English locale settings
        self._locale_settings[Language.ENGLISH] = LocaleSettings(
            date_format="%Y-%m-%d",
            time_format="%H:%M:%S",
            number_format={"decimal_separator": ".", "thousands_separator": ",", "grouping": [3, 3, 0]},
            currency_symbol="$",
            decimal_separator=".",
            thousands_separator=",",
        )

    def set_language(self, language: Language) -> bool:
        """Set the current language."""
        with self._lock:
            if language in self._translations:
                self._current_language = language
                return True
            return False

    def get_current_language(self) -> Language:
        """Get the current language."""
        with self._lock:
            return self._current_language

    def get_language_name(self, language: Language) -> str:
        """Get display name for a language."""
        language_names = {
            Language.ENGLISH: "English",
            Language.SPANISH: "Español",
            Language.FRENCH: "Français",
            Language.GERMAN: "Deutsch",
            Language.CHINESE: "中文",
            Language.JAPANESE: "日本語",
            Language.ARABIC: "العربية",
            Language.RUSSIAN: "Русский",
        }
        return language_names.get(language, "Unknown")

    def get_available_languages(self) -> List[Language]:
        """Get list of available languages."""
        with self._lock:
            return list(self._translations.keys())

    def translate(self, key: str, fallback: Optional[str] = None) -> str:
        """Translate a key to the current language."""
        with self._lock:
            current_trans = self._translations.get(self._current_language)
            if current_trans and key in current_trans.translations:
                return current_trans.translations[key]

            # Try fallback language
            fallback_trans = self._translations.get(self._fallback_language)
            if fallback_trans and key in fallback_trans.translations:
                return fallback_trans.translations[key]

            # Return fallback text or the key itself
            return fallback or key

    def add_translation(self, language: Language, key: str, translation: str):
        """Add or update a translation."""
        with self._lock:
            if language not in self._translations:
                self._translations[language] = Translation(
                    language=language,
                    translations={},
                    locale=self._get_locale_for_language(language),
                    is_rtl=self._is_rtl_language(language),
                )

            self._translations[language].translations[key] = translation

    def load_translations(self, language: Language, file_path: Optional[Path] = None) -> bool:
        """Load translations from a file."""
        if file_path is None:
            file_path = self._get_translation_file(language)

        if not file_path.exists():
            return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                translations_data = json.load(f)

            translation = Translation(
                language=language,
                translations=translations_data.get("translations", {}),
                locale=translations_data.get("locale", self._get_locale_for_language(language)),
                is_rtl=translations_data.get("is_rtl", self._is_rtl_language(language)),
            )

            with self._lock:
                self._translations[language] = translation

            return True
        except Exception:
            return False

    def save_translations(self, language: Language, file_path: Optional[Path] = None) -> bool:
        """Save translations to a file."""
        with self._lock:
            if language not in self._translations:
                return False

            translation = self._translations[language]

            if file_path is None:
                file_path = self._get_translation_file(language)

            try:
                # Create directory if it doesn't exist
                file_path.parent.mkdir(parents=True, exist_ok=True)

                translations_data = {
                    "language": language.name,
                    "locale": translation.locale,
                    "is_rtl": translation.is_rtl,
                    "translations": translation.translations,
                }

                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(translations_data, f, indent=2, ensure_ascii=False)

                return True
            except Exception:
                return False

    def _get_translation_file(self, language: Language) -> Path:
        """Get the translation file path for a language."""
        locale = self._get_locale_for_language(language)
        return self._translation_dir / f"{locale}.json"

    def _get_locale_for_language(self, language: Language) -> str:
        """Get locale code for a language."""
        locale_map = {
            Language.ENGLISH: "en_US",
            Language.SPANISH: "es_ES",
            Language.FRENCH: "fr_FR",
            Language.GERMAN: "de_DE",
            Language.CHINESE: "zh_CN",
            Language.JAPANESE: "ja_JP",
            Language.ARABIC: "ar_SA",
            Language.RUSSIAN: "ru_RU",
        }
        return locale_map.get(language, "en_US")

    def _is_rtl_language(self, language: Language) -> bool:
        """Check if a language is right-to-left."""
        rtl_languages = [Language.ARABIC]
        return language in rtl_languages

    def is_current_language_rtl(self) -> bool:
        """Check if current language is right-to-left."""
        with self._lock:
            current_trans = self._translations.get(self._current_language)
            return current_trans.is_rtl if current_trans else False

    def format_date(self, date_obj: Any, format_str: Optional[str] = None) -> str:
        """Format a date according to current locale."""
        with self._lock:
            locale_settings = self._locale_settings.get(self._current_language)
            if locale_settings:
                format_str = format_str or locale_settings.date_format
                try:
                    if hasattr(date_obj, "strftime"):
                        return date_obj.strftime(format_str)
                    else:
                        # Fallback for string dates
                        return str(date_obj)
                except Exception:
                    pass

            # Fallback to default format
            return str(date_obj)

    def format_time(self, time_obj: Any, format_str: Optional[str] = None) -> str:
        """Format a time according to current locale."""
        with self._lock:
            locale_settings = self._locale_settings.get(self._current_language)
            if locale_settings:
                format_str = format_str or locale_settings.time_format
                try:
                    if hasattr(time_obj, "strftime"):
                        return time_obj.strftime(format_str)
                    else:
                        # Fallback for string times
                        return str(time_obj)
                except Exception:
                    pass

            # Fallback to default format
            return str(time_obj)

    def format_number(self, number: float, decimal_places: int = 2) -> str:
        """Format a number according to current locale."""
        with self._lock:
            locale_settings = self._locale_settings.get(self._current_language)
            if locale_settings:
                try:
                    formatted = f"{number:,.{decimal_places}f}"
                    # Replace separators
                    formatted = formatted.replace(".", locale_settings.decimal_separator)
                    formatted = formatted.replace(",", locale_settings.thousands_separator)
                    return formatted
                except Exception:
                    pass

            # Fallback to default format
            return f"{number:.{decimal_places}f}"

    def format_currency(self, amount: float, currency_symbol: Optional[str] = None) -> str:
        """Format currency according to current locale."""
        with self._lock:
            locale_settings = self._locale_settings.get(self._current_language)
            if locale_settings:
                symbol = currency_symbol or locale_settings.currency_symbol
                formatted_amount = self.format_number(amount, 2)
                return f"{symbol}{formatted_amount}"

            # Fallback format
            return f"${amount:.2f}"

    def detect_system_language(self) -> Language:
        """Detect system language preference."""
        try:
            # Try to detect system locale
            system_locale = locale.getdefaultlocale()[0] if locale.getdefaultlocale() else "en_US"

            # Map to our supported languages
            locale_map = {
                "en": Language.ENGLISH,
                "es": Language.SPANISH,
                "fr": Language.FRENCH,
                "de": Language.GERMAN,
                "zh": Language.CHINESE,
                "ja": Language.JAPANESE,
                "ar": Language.ARABIC,
                "ru": Language.RUSSIAN,
            }

            # Extract language code
            lang_code = system_locale.split("_")[0].lower()
            return locale_map.get(lang_code, Language.ENGLISH)
        except Exception:
            return Language.ENGLISH

    def apply_system_language(self):
        """Apply language based on system preference."""
        system_lang = self.detect_system_language()
        self.set_language(system_lang)

    def get_translation_coverage(self, language: Language) -> float:
        """Get translation coverage percentage for a language."""
        with self._lock:
            if language not in self._translations:
                return 0.0

            # Compare with English (fallback) translations
            english_trans = self._translations.get(Language.ENGLISH)
            if not english_trans:
                return 100.0

            target_trans = self._translations[language]
            total_keys = len(english_trans.translations)
            translated_keys = len(target_trans.translations)

            return (translated_keys / total_keys) * 100.0 if total_keys > 0 else 0.0

    def get_missing_translations(self, language: Language) -> List[str]:
        """Get list of missing translations for a language."""
        with self._lock:
            if language not in self._translations:
                return []

            english_trans = self._translations.get(Language.ENGLISH)
            if not english_trans:
                return []

            target_trans = self._translations[language]
            missing = [key for key in english_trans.translations if key not in target_trans.translations]

            return missing

    def export_translations(self, language: Language, file_path: Path) -> bool:
        """Export translations to a file."""
        with self._lock:
            if language not in self._translations:
                return False

            try:
                translation = self._translations[language]
                data = {
                    "language": language.name,
                    "locale": translation.locale,
                    "is_rtl": translation.is_rtl,
                    "translations": translation.translations,
                }

                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                return True
            except Exception:
                return False

    def import_translations(self, file_path: Path) -> bool:
        """Import translations from a file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            language_name = data.get("language")
            if not language_name:
                return False

            # Map language name to enum
            language_map = {
                "ENGLISH": Language.ENGLISH,
                "SPANISH": Language.SPANISH,
                "FRENCH": Language.FRENCH,
                "GERMAN": Language.GERMAN,
                "CHINESE": Language.CHINESE,
                "JAPANESE": Language.JAPANESE,
                "ARABIC": Language.ARABIC,
                "RUSSIAN": Language.RUSSIAN,
            }

            language = language_map.get(language_name)
            if not language:
                return False

            translation = Translation(
                language=language,
                translations=data.get("translations", {}),
                locale=data.get("locale", self._get_locale_for_language(language)),
                is_rtl=data.get("is_rtl", self._is_rtl_language(language)),
            )

            with self._lock:
                self._translations[language] = translation

            return True
        except Exception:
            return False

    def get_translation_stats(self) -> Dict[str, Any]:
        """Get statistics about translations."""
        with self._lock:
            return {
                "total_languages": len(self._translations),
                "current_language": self._current_language.name,
                "translations_by_language": {
                    lang.name: len(trans.translations) for lang, trans in self._translations.items()
                },
                "coverage_by_language": {
                    lang.name: self.get_translation_coverage(lang) for lang in self._translations.keys()
                },
            }

    def create_translation_template(self, language: Language) -> Dict[str, str]:
        """Create a translation template with all keys from English."""
        with self._lock:
            english_trans = self._translations.get(Language.ENGLISH)
            if not english_trans:
                return {}

            return dict.fromkeys(english_trans.translations.keys(), "")

    def get_rtl_stylesheet(self) -> str:
        """Get RTL-specific stylesheet for current language."""
        if self.is_current_language_rtl():
            return """
            /* RTL Language Support */
            QWidget {
                direction: rtl;
            }

            QHBoxLayout, QVBoxLayout {
                direction: rtl;
            }

            QTableView, QTreeView, QListView {
                layout-direction: rtl;
            }

            QScrollBar {
                layout-direction: rtl;
            }

            /* Adjust text alignment for RTL */
            QLabel, QLineEdit, QTextEdit, QComboBox {
                text-align: right;
            }

            /* Adjust button order for RTL */
            QDialogButtonBox {
                button-layout: 1;
            }
            """
        return ""

    def __del__(self):
        """Clean up i18n resources."""
        self._translations.clear()
        self._locale_settings.clear()


# Singleton instance for easy access
_i18n_manager_instance = None


def get_i18n_manager() -> I18nManager:
    """Get the singleton i18n manager instance."""
    global _i18n_manager_instance
    if _i18n_manager_instance is None:
        _i18n_manager_instance = I18nManager()
    return _i18n_manager_instance


# Convenience functions for common i18n tasks
def translate(key: str, fallback: Optional[str] = None) -> str:
    """Convenience function to translate a key."""
    return get_i18n_manager().translate(key, fallback)


def set_language(language: Language) -> bool:
    """Convenience function to set language."""
    return get_i18n_manager().set_language(language)


def get_current_language() -> Language:
    """Convenience function to get current language."""
    return get_i18n_manager().get_current_language()


def format_date(date_obj: Any, format_str: Optional[str] = None) -> str:
    """Convenience function to format date."""
    return get_i18n_manager().format_date(date_obj, format_str)


def format_number(number: float, decimal_places: int = 2) -> str:
    """Convenience function to format number."""
    return get_i18n_manager().format_number(number, decimal_places)


def format_currency(amount: float, currency_symbol: Optional[str] = None) -> str:
    """Convenience function to format currency."""
    return get_i18n_manager().format_currency(amount, currency_symbol)


# Translation context manager for temporary language switching
class TranslationContext:
    """Context manager for temporary language switching."""

    def __init__(self, language: Language):
        self.language = language
        self.manager = get_i18n_manager()
        self.original_language = None

    def __enter__(self):
        self.original_language = self.manager.get_current_language()
        self.manager.set_language(self.language)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.manager.set_language(self.original_language)


# Translation decorator for functions
def with_translation(language: Language):
    """Decorator to execute function with specific language."""

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            manager = get_i18n_manager()
            original_lang = manager.get_current_language()
            manager.set_language(language)

            try:
                result = func(*args, **kwargs)
            finally:
                manager.set_language(original_lang)

            return result

        return wrapper

    return decorator
