
# During discovery unittest may try to import the real `ui` package which
# requires PyQt6. Provide a lightweight stub package so that import succeeds.
import sys
import types
import os

if 'ui' not in sys.modules:
    stub = types.ModuleType('ui')
    stub.__path__ = [os.path.join(os.path.dirname(__file__), '..', 'ui')]
    sys.modules['ui'] = stub
