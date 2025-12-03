import os
import sys

# Ensure src/ is on sys.path for tests run in environments where package isn't installed
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SRC = os.path.join(ROOT, 'src')
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from dbutils.gui.qt_app import highlight_text_as_html




def test_single_word_highlight():
    text = "user_table column user"
    query = "user"
    html = highlight_text_as_html(text, query)
    # expect 'user' occurrences wrapped in span
    assert html.count('<span') == 2
    assert 'user' in html.lower()


def test_multi_word_highlight():
    text = "first_name last_name email_address"
    query = "name email"
    html = highlight_text_as_html(text, query)
    # both 'name' occurrences and 'email' should be highlighted
    assert html.count('<span') >= 3
    # ensure non-matched text is preserved in pieces (we expect highlights to split words)
    assert 'first_' in html
    assert '_address' in html
