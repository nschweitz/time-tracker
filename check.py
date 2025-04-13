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
chart_height = 44
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
    with open(filepath, 'r') as f:
        key = f.read().strip()
    # Removed error handling for empty or missing file
    return key

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
    print(f"Running command: {' '.join(grim_command)}")
    result = subprocess.run(grim_command, check=True, capture_output=True, text=True)
    print("Screenshot captured successfully.")
    # Removed error handling for grim

    # Read the image file and encode it in base64
    with open(image_path, "rb") as image_file:
        image_bytes = image_file.read()
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    image_data_url = f"data:image/jpeg;base64,{base64_image}"
    # Removed error handling for file reading/encoding

    # Clean up the temporary screenshot file
    os.remove(image_path)
    print(f"Removed temporary file: {image_path}")
    # Removed error handling for os.remove

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
    # Keep this specific error check as requested
    if completion.choices == None:
        print("Backend failed:")
        print(completion)
        return "Fail", "Backend failed"

    result_text = completion.choices[0].message.content
    print(f"LLM Response: {result_text}")

    # --- Second API Call: Categorization ---
    print("Sending request to LLM for categorization...")
    allowed_category_names = list(CATEGORY_COLORS.keys())
    prompt_category_list = []
    for name, (color, description) in CATEGORY_COLORS.items():
        if name != "Unknown":
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
      temperature=0.2,
    )
    category_text = completion.choices[0].message.content.strip()

    # Validate the category against the defined colors
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
    # Removed error handling for the second API call


# --- Chart Update Function ---
def update_chart():
    """Generates or updates the chart based on current data and state."""
    print("Attempting to update chart...")
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
    # Removed error handling for chart generation
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

                # Save the result
                with open(output_filename, "w") as f:
                    f.write(f"{category}\n")
                    f.write(description)
                print(f"Saved analysis to: {output_filename}")
                # Removed error handling for file writing
            else:
                print("Analysis failed or was skipped, not saving data.")
        else:
            print("State is PAUSED, skipping analysis.")


        # --- Generate/Update the chart ---
        update_chart()
        # --- End chart generation ---


        # Wait for the specified delay
        print(f"Waiting for {delay_seconds} seconds...")
        for _ in range(delay_seconds):
            if not is_running and _ > 0:
                 pass
            time.sleep(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Periodically capture screen and analyze activity.")
    parser.add_argument("delay", type=int, help="Delay between captures in seconds.")
    args = parser.parse_args()

    # Removed check for positive delay
    main(args.delay)
