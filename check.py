import argparse
import base64
import os
import subprocess
import time
from datetime import datetime
from openai import OpenAI

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key="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",
)

# Define image path (temporary file)
image_path = "/tmp/screen.jpg"
output_dir = "data"

def capture_and_analyze():
    """Captures screenshot, sends to LLM, and returns the analysis."""
    # Capture the screenshot using grim
    grim_command = ["grim", "-t", "jpeg", "-s", "0.5", image_path]
    try:
        print(f"Running command: {' '.join(grim_command)}")
        result = subprocess.run(grim_command, check=True, capture_output=True, text=True)
        print("Screenshot captured successfully.")
    except FileNotFoundError:
        print("Error: 'grim' command not found. Please ensure it is installed and in your PATH.")
        return None # Indicate failure
    except subprocess.CalledProcessError as e:
        print(f"Error running grim: {e}")
        print(f"Stderr: {e.stderr}")
        return None # Indicate failure
    except Exception as e:
        print(f"An unexpected error occurred during screenshot capture: {e}")
        return None # Indicate failure

    # Read the image file and encode it in base64
    try:
        with open(image_path, "rb") as image_file:
            image_bytes = image_file.read()
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        image_data_url = f"data:image/jpeg;base64,{base64_image}"
    except FileNotFoundError:
        print(f"Error: Screenshot file not found at {image_path} after capture attempt.")
        return None # Indicate failure
    except Exception as e:
        print(f"Error processing image: {e}")
        return None # Indicate failure
    finally:
        # Clean up the temporary screenshot file
        try:
            os.remove(image_path)
            print(f"Removed temporary file: {image_path}")
        except OSError as e:
            print(f"Error removing temporary file {image_path}: {e}")


    # Call the LLM API
    try:
        print("Sending request to LLM...")
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
        result_text = completion.choices[0].message.content
        print(f"LLM Response: {result_text}")
        return result_text
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None # Indicate failure


def main(delay_seconds):
    """Main loop to capture, analyze, save, and wait."""
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    print(f"Ensured output directory exists: {output_dir}")

    while True:
        print(f"\nStarting analysis cycle at {datetime.now().isoformat()}...")
        analysis_result = capture_and_analyze()

        if analysis_result:
            # Generate timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = os.path.join(output_dir, f"{timestamp}.txt")

            # Save the result
            try:
                with open(output_filename, "w") as f:
                    f.write(analysis_result)
                print(f"Saved analysis to: {output_filename}")
            except IOError as e:
                print(f"Error writing analysis to file {output_filename}: {e}")
        else:
            print("Analysis failed, skipping save.")

        # Wait for the specified delay
        print(f"Waiting for {delay_seconds} seconds...")
        time.sleep(delay_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Periodically capture screen and analyze activity.")
    parser.add_argument("delay", type=int, help="Delay between captures in seconds.")
    args = parser.parse_args()

    if args.delay <= 0:
        print("Error: Delay must be a positive integer.")
        exit(1)

    main(args.delay)
