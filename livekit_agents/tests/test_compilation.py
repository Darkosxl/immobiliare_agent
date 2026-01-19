"""
Test 1: Syntax/compilation check for core files.
Verifies that all specified Python files have valid syntax.

To add more files to check, simply add paths to FILES_TO_CHECK.
"""
import py_compile
import os
import pytest

# Root directory of the livekit_agents package
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Files to check for valid Python syntax
# Add new files here as needed
FILES_TO_CHECK = [
    "agents/it_inbound_agent.py",
    "agents/it_outbound_agent.py",
    "prompts/it_inbound_prompt.py",
    "prompts/it_outbound_prompt.py",
    "tools/database.py",
]


@pytest.mark.parametrize("filepath", FILES_TO_CHECK)
def test_file_compiles(filepath):
    """Test that the specified file has valid Python syntax."""
    full_path = os.path.join(ROOT_DIR, filepath)
    
    # Check file exists
    assert os.path.exists(full_path), f"File not found: {filepath}"
    
    # Check syntax is valid (raises py_compile.PyCompileError if invalid)
    try:
        py_compile.compile(full_path, doraise=True)
    except py_compile.PyCompileError as e:
        pytest.fail(f"Syntax error in {filepath}: {e}")
