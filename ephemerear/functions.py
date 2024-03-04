### Imports ###

import os

### End of Imports ###


### Function Definition ###
def add_todo(text, todo_file="bots/donbot/output/responses/todos/todos.md"):
    """
    Adds a new todo item to the end of the 'todos.md' markdown file.

    Parameters:
    text (str): The task description to be added to the todo list.

    Returns:
    text (str): A text alerting the user the memory file was written to, with a preview of the text file written to.
    """

    #
    if not os.path.exists(os.path.dirname(todo_file)):
        os.makedirs(os.path.dirname(todo_file))

    #
    if not os.path.exists(todo_file):
        with open(todo_file, "w") as file:
            file.write("# To-Do List\n\n")

    # Write to the file the
    with open(todo_file, "a") as file:
        file.write(text + "\n")

    # Return string noting that the memory was added to the list, with preview of the text appended to.
    return f"Added the following to-do item to your list: {text[0:100]} ..."

def commit_to_memory(text, memory_file="bots/donbot/output/responses/todos/memory.md"):
    """
    Commits a new memory to the 'memory.md' markdown file.

    Parameters:
    text (str): The content to be added to the memory file.

    Returns:
    text (str): String alerting user memory was added to the list, with preview of the text added to .
    """

    #
    if not os.path.exists(os.path.dirname(memory_file)):
        os.makedirs(os.path.dirname(memory_file))

    #
    if not os.path.exists(memory_file):
        with open(memory_file, "w") as file:
            file.write("# Memories\n\n")

    # Write to the memory file the text.
    with open(memory_file, "a") as file:
        file.write(text + "\n")

    # Return string noting that the memory was added to the list, with preview of the text appended to.
    return f"Added the following memory to your list: {text[0:100]}"

### End of Function Definition ###


### Frozen Variables ###

add_todo_definition = {

    # Define the function name and description of the function.
    "name": "add_todo",
    "description": "Adds a to-do item to the user's todos.md file with the provided text.",

    # Specify the type, properties and required input types
    "parameters": {
        "type": "object",

        "properties": {
            "text": {
                "type": "string",
                "description": "The text of the to-do item to add. "
                               "Be sure to use markdown formatting: "
                               "    (e.g. use \"- [ ]\" for a checkbox, and other styling, for each item."
            }
        },

        "required": ["text"]
    }

}

commit_to_memory_definition = {
            "name": "commit_to_memory",
            "description": "This function commits a piece of text to the user's memory.md markdown file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text content to commit to memory. You can use markdown styling to format the memory entry."
                    }
                },
                "required": ["text"]
            }
        }

### End of Frozen Variables ###