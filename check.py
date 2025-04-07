import argparse
import base64
import argparse
import base64
import os
import signal # Import signal module
import subprocess
import time
from datetime import datetime, date
from openai import OpenAI
from chart import generate_chart, CATEGORY_COLORS

# --- Configuration ---
API_KEY_FILE = "api_key.txt"
AI_MODEL = "google/gemini-flash-1.5-8b"
image_path = "/tmp/screen.jpg" # Temporary screenshot file
output_dir = "data" # Directory for saving analysis results
chart_output_path = "/tmp/time.png" # Path for the generated chart
chart_width = 1000
chart_height = 22
# Allowed categories are now derived from chart.CATEGORY_COLORS.keys()
# --- End Configuration ---

# --- Global State for Signal Handling ---
is_running = True # Start in the running state
# --- End Global State ---

# --- Signal Handler ---
def handle_sigusr1(signum, frame):
    """Toggles the running state when SIGUSR1 is received."""
    global is_running
    previous_state = is_running
    is_running = not is_running
    status = "ENABLED" if is_running else "DISABLED"
    print(f"\nSIGUSR1 received. Analysis toggled to: {status}\n")
    # Regenerate chart immediately if state changed, to reflect pause/resume visually
    if is_running != previous_state:
        update_chart()
# --- End Signal Handler ---


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
        exit(1) # Exit immediately
    except subprocess.CalledProcessError as e:
        print(f"Error running grim: {e}")
        print(f"Stderr: {e.stderr}")
        exit(1) # Exit immediately
    except Exception as e:
        print(f"An unexpected error occurred during screenshot capture: {e}")
        exit(1) # Exit immediately

    # Read the image file and encode it in base64
    try:
        with open(image_path, "rb") as image_file:
            image_bytes = image_file.read()
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        image_data_url = f"data:image/jpeg;base64,{base64_image}"
    except FileNotFoundError:
        print(f"Error: Screenshot file not found at {image_path} after capture attempt.")
        exit(1) # Exit immediately
    except Exception as e:
        print(f"Error processing image: {e}")
        exit(1) # Exit immediately
    finally:
        # Clean up the temporary screenshot file (will run even if exit() was called in except)
        try:
            os.remove(image_path)
            print(f"Removed temporary file: {image_path}")
        except OSError as e:
            print(f"Error removing temporary file {image_path}: {e}")


    # Call the LLM API
    print("Sending request to LLM...")
    completion = client.chat.completions.create(
      model=AI_MODEL,
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
    if completion.choices == None:
        print("Backend failed:")
        print(completion)
        return "Fail", "Backend failed"
    result_text = completion.choices[0].message.content
    print(f"LLM Response: {result_text}")
    # This was the incorrect early return: return result_text

    # --- Second API Call: Categorization ---
    try:
        print("Sending request to LLM for categorization...")
        allowed_category_names = list(CATEGORY_COLORS.keys())
        # Ensure "Unknown" is not presented as an option to the LLM
        # Build the category list with descriptions for the prompt
        prompt_category_list = []
        for name, (color, description) in CATEGORY_COLORS.items():
            if name != "Unknown": # Don't include Unknown as an option for the LLM
                prompt_category_list.append(f"- {name}: {description}")

        categorization_prompt = f"""Given the activity description: "{result_text}"

Please categorize this activity into ONE of the following categories based on their descriptions:
{chr(10).join(prompt_category_list)}

Respond with ONLY the category name (e.g., "Programming", "Social media")."""

        completion = client.chat.completions.create(
          model=AI_MODEL,
          messages=[
            {
              "role": "user",
              "content": categorization_prompt
            }
          ],
          temperature=0.2, # Lower temperature for more deterministic category output
        )
        category_text = completion.choices[0].message.content.strip()

        # Validate the category against the defined colors (excluding "Unknown" as a valid LLM output)
        valid_categories_for_llm = set(CATEGORY_COLORS.keys())
        if "Unknown" in valid_categories_for_llm:
             valid_categories_for_llm.remove("Unknown")

        if category_text in valid_categories_for_llm:
            validated_category = category_text
        else:
            print(f"Warning: LLM returned invalid category '{category_text}'. Defaulting to 'Other'.")
            validated_category = "Other"

        print(f"LLM Category: {validated_category}")
        return validated_category, result_text

    except Exception as e:
        print(f"Error calling OpenAI API for categorization: {e}")
        exit(1) # Exit immediately


# --- Chart Update Function ---
def update_chart():
    """Generates or updates the chart based on current data and state."""
    print("Attempting to update chart...")
    try:
        today = date.today()
        generate_chart(
            data_dir=output_dir,
            output_path=chart_output_path,
            chart_width=chart_width,
            chart_height=chart_height,
            category_colors=CATEGORY_COLORS,
            target_date=today,
            is_active=is_running # Pass the current running state
        )
    except Exception as chart_e:
        # Log chart generation errors but don't stop the main loop
        print(f"Error generating chart: {chart_e}")
# --- End Chart Update Function ---


def main(delay_seconds):
    """Main loop to capture, analyze, save, and wait."""
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    print(f"Ensured output directory exists: {output_dir}")

    # Register the signal handler
    signal.signal(signal.SIGUSR1, handle_sigusr1)
    print(f"Process ID: {os.getpid()}. Send SIGUSR1 to toggle analysis.")
    print(f"Initial state: {'ENABLED' if is_running else 'DISABLED'}")


    while True:
        print(f"\nCycle start at {datetime.now().isoformat()}. State: {'RUNNING' if is_running else 'PAUSED'}")

        category = None
        description = None

        if is_running:
            print("State is RUNNING, performing analysis...")
            category, description = capture_and_analyze()

            if category and description: # Check if analysis was successful
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
                    # Decide if we should exit or continue if saving fails
                    # For now, continue to chart generation
            else:
                # capture_and_analyze might have exited due to errors, or returned None/None
                print("Analysis failed or was skipped, not saving data.")
                # We still proceed to chart generation below
        else:
            print("State is PAUSED, skipping analysis.")


        # --- Generate/Update the chart ---
        # Called at the end of each cycle AND by the signal handler for immediate updates
        update_chart()
        # --- End chart generation ---


        # Wait for the specified delay
        print(f"Waiting for {delay_seconds} seconds...")
        # Use a loop for sleep to make it interruptible by signals more quickly
        # Although signal handlers usually interrupt sleep anyway, this is more robust
        for _ in range(delay_seconds):
            if not is_running and _ > 0: # If paused, check state change immediately after signal
                 pass # No need to sleep full second if state changed
            time.sleep(1)


# Note: The main loop structure was significantly changed in the previous block.
# This block is just to ensure the __main__ part remains correct.
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Periodically capture screen and analyze activity.")
    parser.add_argument("delay", type=int, help="Delay between captures in seconds.")
    args = parser.parse_args()

    if args.delay <= 0:
        print("Error: Delay must be a positive integer.")
        exit(1)

    main(args.delay)
