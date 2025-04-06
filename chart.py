import os
from datetime import datetime, time, date, timedelta, timezone
from PIL import Image, ImageDraw

# Define colors for each category (RGB tuples)
CATEGORY_COLORS = {
    "Programming": (30, 144, 255),    # DodgerBlue
    "Social media": (255, 165, 0),     # Orange
    "Youtube": (255, 0, 0),           # Red
    "Productive stuff in browser": (60, 179, 113), # MediumSeaGreen
    "Spotify": (30, 215, 96),         # Spotify Green
    "Watching stuff": (128, 0, 128),   # Purple
    "Reading news": (210, 105, 30),    # Chocolate
    "Other": (169, 169, 169),         # DarkGray
    "Unknown": (211, 211, 211),       # LightGray (for background/initial state)
}

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

    # Create the image
    image = Image.new('RGB', (chart_width, chart_height), category_colors.get("Unknown", (211, 211, 211)))
    draw = ImageDraw.Draw(image)

    # Calculate seconds per pixel
    seconds_per_pixel = total_duration_seconds / chart_width

    # --- Draw intervals ---
    current_dt = chart_start_dt

    # Draw initial block from 7 AM to the first event (if any)
    if data_points and data_points[0][0] > chart_start_dt:
        end_dt = data_points[0][0]
        start_pixel = 0 # Starts at the beginning
        end_pixel = int((end_dt - chart_start_dt).total_seconds() / seconds_per_pixel)
        color = category_colors.get("Unknown", (211, 211, 211)) # Color before first data point
        if end_pixel > start_pixel:
            print(f"  Drawing initial block: Start={chart_start_dt.isoformat()}, End={end_dt.isoformat()}, Category=Unknown, Pixels=[{start_pixel}, {end_pixel}]")
            draw.rectangle([(start_pixel, 0), (end_pixel, chart_height)], fill=color)
        current_dt = end_dt # Move current time to the first event

    # Draw intervals based on data points
    print("--- Drawing Intervals ---")
    for i, (event_dt, category) in enumerate(data_points):
        start_interval_dt = max(event_dt, current_dt) # Start from event time or last position

        # Determine end time: next event or chart end
        if i + 1 < len(data_points):
            end_interval_dt = min(data_points[i+1][0], chart_end_dt)
        else:
            end_interval_dt = chart_end_dt

        # Ensure we don't draw past the chart end time
        end_interval_dt = min(end_interval_dt, chart_end_dt)

        if start_interval_dt < end_interval_dt: # Only draw if interval has positive duration
            # Calculate pixel positions
            start_pixel = int((start_interval_dt - chart_start_dt).total_seconds() / seconds_per_pixel)
            end_pixel = int((end_interval_dt - chart_start_dt).total_seconds() / seconds_per_pixel)

            # Clamp pixel values to chart bounds
            start_pixel = max(0, start_pixel)
            end_pixel = min(chart_width, end_pixel)

            color = category_colors.get(category, category_colors.get("Other")) # Use category color, fallback to Other

            if end_pixel > start_pixel: # Ensure width is positive
                print(f"  Drawing interval: Start={start_interval_dt.isoformat()}, End={end_interval_dt.isoformat()}, Category={category}, Pixels=[{start_pixel}, {end_pixel}]")
                draw.rectangle([(start_pixel, 0), (end_pixel, chart_height)], fill=color)
            else:
                 print(f"  Skipping zero/negative width interval: Start={start_interval_dt.isoformat()}, End={end_interval_dt.isoformat()}, Category={category}, Pixels=[{start_pixel}, {end_pixel}]")


        # Update current_dt for the next iteration (or the final fill)
        current_dt = end_interval_dt
        if current_dt >= chart_end_dt:
             break # Stop if we've reached the end of the chart

    # Fill any remaining time at the end with the last known category (if needed)
    # This part might be redundant due to the loop structure, but kept for clarity
    if current_dt < chart_end_dt:
         start_pixel = int((current_dt - chart_start_dt).total_seconds() / seconds_per_pixel)
         end_pixel = chart_width
         last_category = data_points[-1][1] if data_points else "Unknown"
         color = category_colors.get(last_category, category_colors.get("Other"))
         if end_pixel > start_pixel:
             print(f"  Drawing final block: Start={current_dt.isoformat()}, End={chart_end_dt.isoformat()}, Category={last_category}, Pixels=[{start_pixel}, {end_pixel}]")
             draw.rectangle([(start_pixel, 0), (end_pixel, chart_height)], fill=color)
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
