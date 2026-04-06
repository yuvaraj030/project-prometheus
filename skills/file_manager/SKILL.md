---
name: file_manager
description: Read, write, list, and manage files and directories on the local system
tools:
  - read_file
  - write_file
  - list_directory
  - delete_file
---

# File Manager Skill

You can read, write, and manage files and directories on the user's computer.

## When to Use
- User asks to read, create, edit, or delete a file
- User wants to list contents of a directory
- User asks to organize or rename files
- User wants to find a specific file

## Tools Available

### read_file
Read the contents of a file.
- **path** (string, required): Absolute or relative path to the file
- Returns: The file contents as text

### write_file
Create or overwrite a file with new content.
- **path** (string, required): Path where the file should be written
- **content** (string, required): The content to write
- Returns: Confirmation with file path and size

### list_directory
List files and subdirectories in a directory.
- **path** (string, required): Path to the directory
- **recursive** (boolean, optional): Whether to list recursively (default: false)
- Returns: List of files with names, sizes, and types

### delete_file
Delete a file (with confirmation).
- **path** (string, required): Path to the file to delete
- Returns: Confirmation of deletion

## Instructions
1. Always use absolute paths when possible
2. Before writing, confirm with the user if overwriting an existing file
3. Be careful with delete operations — always confirm first
4. When listing directories, format output cleanly
