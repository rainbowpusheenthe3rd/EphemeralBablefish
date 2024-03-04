### Imports ###

import tiktoken

### End of Imports ###


### Function Definition ###

# For a given text, counts the number of tokens. Defaults to p50k_base encoding for token count.
def count_tokens(text, encoding_name = 'p50k_base'):
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(text))
    return num_tokens

# Chunks a document into at-most 15 character parts and searches for a target word in the strings.
def test_for_word(text, word, splitrange=15):

    # If None passed, return False. No string to match substring against. Creato ex nihilo.
    if text is None:
        return False

    # Split the text by space delimiters or splitrange, whichever is lowest.
    splitrange = min(splitrange, len(text.split()))
    text_split = text.lower().split()[:splitrange]

    # Test for existence of substring in string. Uses any and in to halt iteration early if found.
    return any(word in split_word for split_word in text_split)

### End of Function Definition ###
























