import argparse
import base64
import os
import subprocess
import time
from datetime import datetime
from openai import OpenAI

# --- Configuration ---
API_KEY_FILE = "api_key.txt"
image_path = "/tmp/screen.jpg"
output_dir = "data"
ALLOWED_CATEGORIES = {
    "Programming",
    "Social media",
    "Youtube",
    "Productive stuff in browser",
    "Spotify",
    "Watching stuff",
    "Reading news",
    "Other",
}
# --- End Configuration ---

# --- Helper Functions ---
def load_api_key(filepath):
    """Loads the API key from the specified file."""
    try:
        with open(filepath, 'r') as f:
            key = f.read().strip()
        if not key:
            print(f"Error: API key file '{filepath}' is empty.")
            exit(1)
        return key
    except FileNotFoundError:
        print(f"Error: API key file '{filepath}' not found.")
        print("Please create this file and place your OpenRouter API key in it.")
        exit(1)
    except Exception as e:
        print(f"Error reading API key file '{filepath}': {e}")
        exit(1)

# --- Load API Key ---
api_key = load_api_key(API_KEY_FILE)

# --- Initialize OpenAI Client ---
client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=api_key,
)


# --- Core Logic ---
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
        # This was the incorrect early return: return result_text
    except Exception as e:
        print(f"Error calling OpenAI API for description: {e}")
        return None, None # Indicate failure, returning two values as expected by main

    # --- Second API Call: Categorization ---
    try:
        print("Sending request to LLM for categorization...")
        categorization_prompt = f"""Given the activity description: "{result_text}"

Please categorize this activity into one of the following categories ONLY:
{', '.join(ALLOWED_CATEGORIES)}

Respond with ONLY the category name."""

        completion = client.chat.completions.create(
          model="google/gemini-2.0-flash-thinking-exp:free", # Or another suitable model
          messages=[
            {
              "role": "user",
              "content": categorization_prompt
            }
          ],
          temperature=0.2, # Lower temperature for more deterministic category output
        )
        category_text = completion.choices[0].message.content.strip()

        # Validate the category
        if category_text in ALLOWED_CATEGORIES:
            validated_category = category_text
        else:
            print(f"Warning: LLM returned invalid category '{category_text}'. Defaulting to 'Other'.")
            validated_category = "Other"

        print(f"LLM Category: {validated_category}")
        return validated_category, result_text

    except Exception as e:
        print(f"Error calling OpenAI API for categorization: {e}")
        # Decide how to handle categorization failure: default to Other or skip?
        # Defaulting to Other here.
        print("Defaulting category to 'Other' due to API error.")
        return "Other", result_text


def main(delay_seconds):
    """Main loop to capture, analyze, save, and wait."""
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    print(f"Ensured output directory exists: {output_dir}")

    while True:
        print(f"\nStarting analysis cycle at {datetime.now().isoformat()}...")
        category, description = capture_and_analyze()

        if category and description: # Check if both were returned successfully
            # Generate timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = os.path.join(output_dir, f"{timestamp}.txt")

            # Save the result (category on first line, description on second)
            try:
                with open(output_filename, "w") as f:
                    f.write(f"{category}\n")
                    f.write(description)
                print(f"Saved analysis to: {output_filename}")
            except IOError as e:
                print(f"Error writing analysis to file {output_filename}: {e}")
        else:
            print("Analysis or categorization failed, skipping save.")

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
