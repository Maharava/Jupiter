import os
import pyaudio
import numpy as np
from openwakeword.model import Model

def load_oww_model(args):
    if args.model_path != "":
        return Model(wakeword_models=[args.model_path], inference_framework=args.inference_framework)
    else:
        return Model(inference_framework=args.inference_framework)
