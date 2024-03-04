### Imports ###

# Standard Python libraries
import datetime
import inspect
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

# Third party libraries
import openai
import requests
from requests.exceptions import RequestException

# Within module imports
import EphemeralBablefish.ephemerear.functions as eefunctions
from .documentModification import count_tokens
from .earIO import load_yaml_to_dict

### End of Imports ###


### Function Definition ###

# LLM agent using predefined config and sys prompts.
# Manages message history, sends Pushover notifications, and stores responses in Markdown format.
class EphemerEar:

    # Instantiate the class utilising the details in the config.yaml
    def __init__(self, config_path: str = 'config.yaml') -> None:

        # Load the project-level settings in the config.yaml into an in-memory Python dictionary for operations.
        self.config = load_yaml_to_dict(config_path)
        verify_and_create_paths(self.config)

        # Get the history file path from the location of the history file.
        history_file_path_str = self.config['bot']['history_file']
        self.history_file_path = Path(history_file_path_str)
        # Instead, set history_file_path to us config['bot']['root_dir'] plus the history_file path

        # Set the system prompt, api_key, model to use, key for pushover, pushover use, notify setting, user history.
        self.system_prompt = self.make_system_prompt()
        self.api_key = self.config['auth_tokens']['openai']
        self.model = self.config['bot']['model']
        self.pushover_key = self.config['auth_tokens'].get('pushover_key', '')
        self.pushover_user = self.config['auth_tokens'].get('pushover_user', '')
        self.notify = bool(self.pushover_key and self.pushover_user and self.config['bot']['use_pushover'])
        self.initialize_history_file()

        # Derive available functions from the functions file.
        self.functions_module = eefunctions
        self.available_functions, self.functions_definitions = self._load_functions_from_module(self.functions_module)


    #
    def _load_functions_from_module(self, module):

            # Define placeholder structures to update, used in creating functions_definitions in format OpenAI expects
            functions_dict = {}
            function_definitions_list = []
            
            for name, obj in inspect.getmembers(module):
                if inspect.isfunction(obj):
                    # Store the function in a dictionary for potential execution
                    functions_dict[name] = obj
                    
                # Assuming every function has a corresponding definition following the naming convention
                definition_var_name = f"{name}_definition"
                definition = getattr(module, definition_var_name, None)
                if definition:
                    # Append the function definition to the list
                    function_definitions_list.append(definition)
                    
            # Wrap the list of function definitions in the structure expected by the OpenAI API
            functions_definitions = {"functions": function_definitions_list, "function_call": "auto"}

            return functions_dict, functions_definitions


    # Returns the system_prompt formatted with the user name, user_details, and bot name.
    def make_system_prompt(self) -> str:
        # Retrieve paths for the user details and the system prompt.
        system_prompt_path = Path(self.config['bot']['system_prompt'])
        user_details_path = Path(self.config['user']['user_details'])

        # Check whether the user details and system prompt data exists in defined files
        if not system_prompt_path.is_file() or not user_details_path.is_file():
            raise FileNotFoundError("Required file for system prompt or user details is missing.")

        # Get user details and system prompt from saved files. Update to use SQLite.
        with system_prompt_path.open('r') as file:
            system_prompt = file.read()
        with user_details_path.open('r') as file:
            user_details = file.read()

        # Return username, the bot name, and the details for the user.
        return system_prompt.format(user_name=self.config['user']['name'],
                                    user_details=user_details,
                                    bot_name=self.config['bot']['name'])

    def initialize_history_file(self) -> None:
        if not self.history_file_path.is_file():
            with self.history_file_path.open('w') as file:
                json.dump([], file)

    def get_history(self) -> List[Dict[str, str]]:
        with self.history_file_path.open('r') as file:
            return json.load(file)

    def save_history(self, history: List[Dict[str, str]]) -> None:
        for message in history:
            if 'role' in message and message['role'] == 'system':
                history.remove(message)
        with self.history_file_path.open('w') as file:
            json.dump(history, file)

    def send_pushover(self,
        title: str,
        message: str,
        user_key: str,
        api_key: str,
        message_url: Optional[str] = None
        ) -> requests.Response:
            if not title:
                raise ValueError("The title must not be empty.")
            if not user_key:
                raise ValueError("The user_key must not be empty.")
            if not api_key:
                raise ValueError("The api_key must not be empty.")

            url = "https://api.pushover.net/1/messages.json"
            data = {
                "title": title,
                "token": api_key,
                "user": user_key,
                "message": message,
                "url": message_url
            }
            
            try:
                response = requests.post(url, data=data)
                response.raise_for_status()
                return response
            except RequestException as e:
                raise RequestException(f"Failed to send the message: {e}")

    #
    def gpt_chat(self,
                 message: str,
                 model: str = "gpt-3.5-turbo-16k",
                 max_tokens: int = 800,
                 notify: bool = True,
                 available_functions: dict = None) -> str:

        # Establish a model and message history.
        history = self.get_history()
        model = self.model
        notify = self.notify
        messages = history.copy()
        messages.append({"role": "user", "content": message})

        # If available_functions is not set, inherit from class
        if available_functions is None:
            available_functions = self.functions_definitions["functions"]

        max_message_window = self.config['bot']['max_message_window']

        # Filter to exclude system messages and reverse the list to start from the oldest
        non_system_messages = list(filter(lambda m: m['role'] != 'system', messages))

        # Compute the token count and remove messages if necessary
        running_token_count = 0
        for m in non_system_messages:
            token_count = count_tokens(m['content'])
            if running_token_count + token_count > max_message_window:
                # When limit is exceeded, continue removing from the oldest
                non_system_messages.pop()
            else:
                running_token_count += token_count

        # Recombine non system messages with a dictionary that contains the system prompt.
        all_messages = [{"role": "system", "content": self.system_prompt}] + non_system_messages

        # Make a call to the OpenAI APIs and get the bot response.
        completion = openai.ChatCompletion.create(
            model=model,
            messages=all_messages,
            max_tokens=max_tokens,
            functions=available_functions if available_functions else None,
            api_key=self.api_key
        )
        bot_response = completion.choices[0].message

        # Handle the response
        if 'content' in bot_response and bot_response['content'] is not None:
            confirmation_message = bot_response['content']
        elif 'function_call' in bot_response:
            func_name = bot_response['function_call']['name']
            func_args = bot_response['function_call']['arguments']

            # JSON parsing of arguments if necessary
            if isinstance(func_args, str):
                func_args = json.loads(func_args)

            # Argument type conversion for dates
            for key in ['date', 'when', 'start', 'end']:
                if key in func_args:
                    func_args[key] = datetime.datetime.fromisoformat(func_args[key])

            # Dynamically calling the function
            if func_name in self.available_functions:
                function_to_call = self.available_functions[func_name]
                function_response = function_to_call(**func_args)
                confirmation_message = f"Function '{func_name}' executed with response: {function_response}"
            else:
                confirmation_message = f"Function '{func_name}' is not available."
        else:
            confirmation_message = "Received a response without 'content' or 'function_call'."

        # Append to history, save, and handle notifications as before
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": confirmation_message})
        self.save_history(history)
        self.write_response_to_markdown(message, confirmation_message)
        if notify:
            self.send_pushover(title="ephemerear",
                               message=f"Response: {confirmation_message}",
                               user_key=self.pushover_user,
                               api_key=self.pushover_key)

        if notify:
            self.send_pushover(
                title="ephemerear",
                message=f"Response written to MD: {confirmation_message}",
                user_key=self.pushover_user,
                api_key=self.pushover_key,
                message_url=None  # or a URL if applicable
            )

        return confirmation_message

    def write_response_to_markdown(self, user_message: str, bot_response: str) -> None:
        response_output_dir = self.config['stores']['responses']
        now = datetime.datetime.now()
        current_year = now.strftime("%Y")
        current_month = now.strftime("%m")
        year_month_dir = os.path.join(response_output_dir, current_year, current_month)
        os.makedirs(year_month_dir, exist_ok=True)
        
        unique_identifier = now.strftime("%Y-%m-%d_at_%H-%M-%S")
        description = "response"  

        response_filename = f"{unique_identifier}_{description}.md"
        response_filepath = os.path.join(year_month_dir, response_filename)

        response_content = f"""## User enquiry
{user_message}

## {self.config['bot']['name']} response
{bot_response}"""
        with open(response_filepath, 'w', encoding='utf-8') as response_file:
            response_file.write(response_content)
        
def verify_and_create_paths(config: dict) -> None:
    user_name = config.get('user', {}).get('name', 'As yet unnamed User')  # Default user name if not provided
    
    for section, settings in config.items():
        if isinstance(settings, dict):
            for key, value in settings.items():
                if isinstance(value, str):
                    path = Path(value)
                    if '/' in value:
                        # Check if the path has a file name with an extension
                        if '.' in path.name:
                            # If the path includes a file name, get the parent directory
                            directory = path.parents[0]
                        else:
                            # It is a directory path
                            directory = path
                        
                        # Create directory if it doesn't exist
                        if not directory.exists():
                            directory.mkdir(parents=True, exist_ok=True)

                    # If it's a file and doesn't exist, create it
                    if '.' in path.name and not path.exists():
                        # If the filename is 'knowledge.json', skip it
                        if path.name == 'history.json':
                            continue
                        path.touch()

                        # Specific case for 'system_prompt'
                        if key == 'system_prompt':
                            with open(path, 'w') as f:
                                f.write(f"""About {{user_name}}, who you're talking to:

{{user_details}}

{{user_name}}'s 'user' messages will be sent to you via transcription. 

Be sensitive to the fact that some user messages may contain misspellings or 'similar' phonetic spellings due to limitations in the transcription engine.

Your name is {{bot_name}}.

---""")

                        # Specific case for 'user.user_details'
                        if key == 'user_details':
                            with open(path, 'w') as f:
                                f.write(f"## About {user_name}\n{user_name} hasn't provided any details yet. Be nice to them!\n")
