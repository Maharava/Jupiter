# IO Wake Word

This is an adapter package that provides a consistent interface to the wake word detection system.

The actual implementation is in `utils/io/io.py`. This package just provides compatibility layers to maintain backward compatibility with code that expects the old module structure.

## Usage

```python
from io_wake_word.audio import AudioCapture, FeatureExtractor
from io_wake_word.models import WakeWordDetector

# Initialize components
detector = WakeWordDetector(model_path="path/to/model.pth")
audio = AudioCapture()

# Register callback
detector.register_detection_callback(my_callback_function)

# Start detection
detector.start()
audio.start()
```
