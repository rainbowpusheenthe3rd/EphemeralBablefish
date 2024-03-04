import datetime
import os
import sys

import ephemerear.transcribe as ts
from ephemerear.EphemerEar import EphemerEar


BOT_PATH = '/Users/donalphipps/Documents/aiphoria/ephemerear'
sys.path.append(BOT_PATH)

os.chdir(BOT_PATH)



audio_filename = sys.argv[1]
print(f"Running at {datetime.datetime.now()} on filename {audio_filename}")

YAML_PATH = f"{BOT_PATH}/donbot.yaml"
ee = EphemerEar(YAML_PATH)

if ee.notify:
    ee.send_pushover("ephemerear Transcription started",
                     f"Running transcription on  {audio_filename}",
                     ee.pushover_user,
                     ee.pushover_key)
transcript_path = f"{ee.config['stores']['transcripts']}"
cache_path = f"{ee.config['bot']['cache']}"
transcript_text = ts.handle_audio(audio_filename, ee.api_key, "", transcript_path, cache_path, config_file = YAML_PATH)

if ee.notify:
    ee.send_pushover("Transcription complete",
                     "Transcription of " + audio_filename + " is complete",
                     ee.pushover_user,
                     ee.pushover_key)