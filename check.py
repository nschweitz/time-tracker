import base64
import io
from PIL import Image
from openai import OpenAI

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key="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",
)

# Load, resize, and encode the image
image_path = "/tmp/screen.png"
try:
    img = Image.open(image_path)
    img = img.resize((960, 540))

    # Save to a buffer with specified quality
    buffer = io.BytesIO()
    img.save(buffer, format="PNG", quality=90) # Assuming PNG, adjust if needed. Use optimize=True for potentially smaller files.
    buffer.seek(0)

    # Encode to base64
    base64_image = base64.b64encode(buffer.read()).decode('utf-8')
    image_data_url = f"data:image/png;base64,{base64_image}" # Adjust mime type if not PNG

except FileNotFoundError:
    print(f"Error: Image file not found at {image_path}")
    exit(1)
except Exception as e:
    print(f"Error processing image: {e}")
    exit(1)


completion = client.chat.completions.create(
  model="openai/gpt-4o",
  messages=[
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "What's in this image?"
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
