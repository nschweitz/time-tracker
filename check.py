import base64
import subprocess
from openai import OpenAI

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key="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",
)

# Define image path
image_path = "/tmp/screen.jpg"

# Capture the screenshot using grim
grim_command = ["grim", "-t", "jpeg", "-s", "0.5", image_path]
try:
    print(f"Running command: {' '.join(grim_command)}")
    result = subprocess.run(grim_command, check=True, capture_output=True, text=True)
    print("Screenshot captured successfully.")
except FileNotFoundError:
    print("Error: 'grim' command not found. Please ensure it is installed and in your PATH.")
    exit(1)
except subprocess.CalledProcessError as e:
    print(f"Error running grim: {e}")
    print(f"Stderr: {e.stderr}")
    exit(1)
except Exception as e:
    print(f"An unexpected error occurred during screenshot capture: {e}")
    exit(1)


# Read the image file and encode it in base64
try:
    with open(image_path, "rb") as image_file:
        image_bytes = image_file.read()
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    image_data_url = f"data:image/jpeg;base64,{base64_image}"

except FileNotFoundError:
    print(f"Error: Screenshot file not found at {image_path} after capture attempt.")
    exit(1)
except Exception as e:
    print(f"Error processing image: {e}")
    exit(1)


completion = client.chat.completions.create(
  model="google/gemini-2.0-flash-thinking-exp:free",
  messages=[
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "Here's my screen. What am I doing? For time tracking purposes. Answer in one sentence."
        },
        {
          "type": "image_url",
          "image_url": {
            "url": image_data_url
          }
        }
      ]
    }
  ],
)

print(completion.choices[0].message.content)
