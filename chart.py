import os
from datetime import datetime, time, date, timedelta, timezone
from PIL import Image, ImageDraw

# Define colors and descriptions for each category
# Format: "Category Name": ( (R, G, B), "Description for LLM" )
CATEGORY_COLORS = {
    "Programming":              ( (30, 144, 255), "Writing code, debugging, using IDEs, terminal tasks related to coding." ),
    "Social media":             ( (255, 165, 0),  "Browsing Reddit, forums (e.g., guitar, Blind), Hacker News, etc." ),
    "Youtube":                  ( (255, 0, 0),    "Watching videos on Youtube." ),
    "Productive browser":       ( (60, 179, 113), "Reading technical documentation, research papers, LeetCode, Stack Overflow, work-related web apps." ),
    "Spotify":                  ( (30, 215, 96),  "Listening to music or podcasts on Spotify." ),
    "Watching stuff":           ( (128, 0, 128),  "Watching videos (not Youtube), movies, TV shows (e.g., Plex, Netflix)." ),
    "Reading news":             ( (210, 105, 30), "Reading news websites or aggregators." ),
    "Other":                    ( (169, 169, 169),"Anything that doesn't fit well into other categories (e.g., file browsing, system settings)." ),
    # Internal category, not shown to LLM
    "Unknown":                  ( (211, 211, 211),"Time before first data point or gaps between activities." ),
}
MAX_VALIDITY_SECONDS = 90

def read_data(data_dir: str, target_date: date) -> list[tuple[datetime, str]]:
    """Reads data files for the target date and returns sorted list of (timestamp, category)."""
    data_points = []
    target_date_str = target_date.strftime("%Y%m%d")

    try:
        for filename in os.listdir(data_dir):
            if filename.startswith(target_date_str) and filename.endswith(".txt"):
                filepath = os.path.join(data_dir, filename)
                try:
                    # Extract timestamp from filename
                    timestamp_str = filename.split('.')[0]
                    dt_obj = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    # Make datetime timezone-aware (assuming local time)
                    dt_obj = dt_obj.replace(tzinfo=datetime.now().astimezone().tzinfo)


                    with open(filepath, 'r') as f:
                        category = f.readline().strip()
                        if category: # Ensure category is not empty
                            data_points.append((dt_obj, category))
                        else:
                            print(f"Warning: Empty category in file {filename}")

                except (ValueError, IndexError) as e:
                    print(f"Warning: Could not parse file {filename}: {e}")
                except Exception as e:
                    print(f"Warning: Error reading file {filename}: {e}")

    except FileNotFoundError:
        print(f"Warning: Data directory '{data_dir}' not found.")
        return [] # Return empty list if directory doesn't exist
    except Exception as e:
        print(f"Error listing data directory '{data_dir}': {e}")
        return []

    # Sort by timestamp
    data_points.sort(key=lambda x: x[0])
    return data_points


def generate_chart(
    data_dir: str,
    output_path: str,
    chart_width: int,
    chart_height: int,
    category_colors: dict,
    target_date: date
):
    """Generates the timeline chart image for the target date."""
    print(f"Generating chart for {target_date.isoformat()}...")

    # Define the time range for the chart (7 AM to midnight)
    # Ensure we use timezone-aware datetimes consistent with data reading
    local_tz = datetime.now().astimezone().tzinfo
    chart_start_dt = datetime.combine(target_date, time(7, 0), tzinfo=local_tz)
    chart_end_dt = datetime.combine(target_date + timedelta(days=1), time(0, 0), tzinfo=local_tz)
    total_duration_seconds = (chart_end_dt - chart_start_dt).total_seconds()

    if total_duration_seconds <= 0:
        print("Error: Invalid time range for chart.")
        return

    # Read and sort data points for the target date
    data_points = read_data(data_dir, target_date)

    # Filter points outside the chart's time range (just in case)
    data_points = [dp for dp in data_points if chart_start_dt <= dp[0] < chart_end_dt]

    print(f"--- Chart Data Points ({len(data_points)}) ---")
    for dt, cat in data_points:
        print(f"  {dt.isoformat()} - {cat}")
    print("--------------------------")

    # Create the image - access color tuple using [0]
    unknown_color_tuple = category_colors.get("Unknown", ((211, 211, 211), ""))[0]
    image = Image.new('RGB', (chart_width, chart_height), unknown_color_tuple)
    draw = ImageDraw.Draw(image)

    # Calculate seconds per pixel
    seconds_per_pixel = total_duration_seconds / chart_width
    unknown_color = category_colors.get("Unknown", ((211, 211, 211), ""))[0] # Extract color

    # Helper to draw a rectangle
    def draw_segment(start_dt, end_dt, color_tuple, category_name): # Pass the whole tuple initially
        color = color_tuple[0] # Extract the RGB color
        if start_dt >= end_dt:
            return # Skip zero or negative duration

        start_pixel = int((start_dt - chart_start_dt).total_seconds() / seconds_per_pixel)
        end_pixel = int((end_dt - chart_start_dt).total_seconds() / seconds_per_pixel)

        # Clamp pixel values
        start_pixel = max(0, start_pixel)
        end_pixel = min(chart_width, end_pixel)

        if end_pixel > start_pixel:
            print(f"  Drawing segment: Start={start_dt.isoformat()}, End={end_dt.isoformat()}, Category={category_name}, Pixels=[{start_pixel}, {end_pixel}]")
            draw.rectangle([(start_pixel, 0), (end_pixel, chart_height)], fill=color)
        # else:
        #     print(f"  Skipping zero-width segment: Start={start_dt.isoformat()}, End={end_dt.isoformat()}, Category={category_name}, Pixels=[{start_pixel}, {end_pixel}]")


    # --- Draw intervals ---
    print("--- Drawing Intervals ---")
    current_dt = chart_start_dt

    for i, (event_dt, category) in enumerate(data_points):
        # Ensure event is within chart bounds (already filtered, but good practice)
        event_dt = max(event_dt, chart_start_dt)
        event_dt = min(event_dt, chart_end_dt)

        # 1. Draw "Unknown" gap before this event
        if event_dt > current_dt:
            # Pass the full tuple for Unknown category
            draw_segment(current_dt, event_dt, category_colors["Unknown"], "Unknown (Gap)")
            current_dt = event_dt # Move pointer to start of event

        # 2. Determine the end of this event's colored block
        max_valid_end_dt = event_dt + timedelta(seconds=MAX_VALIDITY_SECONDS)
        next_event_start_dt = data_points[i+1][0] if i + 1 < len(data_points) else chart_end_dt
        colored_block_end_dt = min(max_valid_end_dt, next_event_start_dt, chart_end_dt)

        # 3. Draw the actual category block
        # Get the tuple (color, description), fallback to Other's tuple
        color_desc_tuple = category_colors.get(category, category_colors["Other"])
        draw_segment(current_dt, colored_block_end_dt, color_desc_tuple, category)

        # 4. Update current_dt
        current_dt = colored_block_end_dt

        # Check if we've reached the end
        if current_dt >= chart_end_dt:
            break

    # Fill any remaining time at the end with "Unknown"
    if current_dt < chart_end_dt:
        # Pass the full tuple for Unknown category
        draw_segment(current_dt, chart_end_dt, category_colors["Unknown"], "Unknown (End Gap)")

    print("-----------------------")

    # Save the image
    try:
        image.save(output_path)
        print(f"Chart saved to: {output_path}")
    except Exception as e:
        print(f"Error saving chart image to {output_path}: {e}")

if __name__ == '__main__':
    # Example usage: Generate chart for today and save to /tmp/time.png
    print("Running chart generation directly (for testing)...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, 'data')
    output_file = '/tmp/time.png'
    chart_w = 1000
    chart_h = 22
    today = date.today()

    # Ensure data directory exists for testing
    os.makedirs(data_dir, exist_ok=True)
    # You might want to create dummy data files in 'data/' for testing

    generate_chart(data_dir, output_file, chart_w, chart_h, CATEGORY_COLORS, today)
    print("Chart generation test finished.")
