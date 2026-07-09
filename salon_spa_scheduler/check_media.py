import os
from PIL import Image

brain_dir = '/Users/developer/.gemini/antigravity/brain/ab516ef2-df53-4a97-b7be-0498f5f4d7fb'
files = [f for f in sorted(os.listdir(brain_dir)) if f.startswith('media__')]
for idx, f in enumerate(files):
    path = os.path.join(brain_dir, f)
    img = Image.open(path)
    print(f"media_{idx} ({f}): size={img.size}, format={img.format}")
