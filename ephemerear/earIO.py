### Imports ###

import yaml

# from metabeaver.fileIO.yamlIO import load_yaml_to_dict
from pathlib import Path
from typing import Any, Dict

### End of Imports ###

### Function Definiton ###

# Given a valid filepath for the project configuration settings, will return yaml as a Python dict.
def load_yaml_to_dict(config_path: str= 'config.yaml') -> Dict[str, Any]:

    yaml_config_path = Path(config_path).resolve()

    # Raise FileNotFoundError if the provided path is actually invalid.
    if not yaml_config_path.is_file():
        raise FileNotFoundError(f"The file {config_path} does not exist.")

    # If we got a valid
    with yaml_config_path.open('r') as file:
        try:
            config = yaml.safe_load(file)
            return config
        except yaml.YAMLError as exc:
            raise ValueError(f"Error parsing YAML file: {exc}")


    return config

### End of Function Definition ###




























