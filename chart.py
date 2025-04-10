import os
from datetime import datetime, time, date, timedelta, timezone
from PIL import Image, ImageDraw

# Define colors and descriptions for each category
# Format: "Category Name": ( (R, G, B), "Description for LLM" )
CATEGORY_COLORS = {
    "Work":                     ( (0, 255, 255), "Writing code, reading docs online, talking to chatbot about programming, leetcode in browser, reading papers, working on CV, job applications, preparing for interview, emails"),
    "Entertainment":            ( (127, 127, 127),  "Reddit, Hacker News, Nate Silver, Lemmy, XKCD, Spotify" ),
    "Watching stuff":           ( (255, 255, 255),  "Youtube, movies, TV shows" ),
    "Reading news":             ( (255, 127, 0), "'Real' newspapers like the Economist or WSJ or SZ. Hacker News does NOT count." ),
    "Other":                    ( (255, 0, 255), "Anything else" ),
    # Internal category, not shown to LLM
    "Unknown":                  ( (0, 0, 0), "N/A" ),
    # Backend failed
    "Fail":                     ( (0, 255, 0), "N/A" ),
}
MAX_VALIDITY_SECONDS = 70

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
    target_date: date,
    is_active: bool # Add parameter to indicate if analysis is active
):
    """Generates the timeline chart image for the target date."""
    print(f"Generating chart for {target_date.isoformat()} (Active: {is_active})...")

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

    # --- Draw Hour Ticks ---
    print("--- Drawing Hour Ticks ---")
    tick_color = (255, 255, 255) # White
    start_hour = chart_start_dt.hour # Should be 7
    end_hour = chart_end_dt.hour   # Should be 0 (midnight)

    # Iterate from the first hour (7 AM) up to the hour before midnight (23:00 or 11 PM)
    for hour in range(start_hour, 24): # 7 through 23
        tick_dt = datetime.combine(target_date, time(hour, 0), tzinfo=local_tz)

        # Calculate pixel position for the hour tick
        if tick_dt >= chart_start_dt and tick_dt < chart_end_dt:
            time_offset_seconds = (tick_dt - chart_start_dt).total_seconds()
            tick_x = int(time_offset_seconds / seconds_per_pixel)

            # Determine tick width
            if hour == 9 or hour == 17: # 9 AM or 5 PM
                tick_width = 3
                # Adjust x for wider lines to center them (optional, but looks better)
                # For a 3px line, draw from x-1 to x+1. draw.line handles width.
                # We might need to draw a rectangle for >1px width if draw.line width param isn't reliable
                print(f"  Drawing wide tick at {hour}:00 (x={tick_x})")
                # Use draw.line with width parameter
                draw.line([(tick_x, 0), (tick_x, chart_height)], fill=tick_color, width=tick_width)
            else:
                tick_width = 1
                print(f"  Drawing tick at {hour}:00 (x={tick_x})")
                draw.line([(tick_x, 0), (tick_x, chart_height)], fill=tick_color, width=tick_width)

    print("------------------------")

    # --- Draw Paused Indicator (if needed) ---
    if not is_active:
        print("--- Drawing Paused Indicator ---")
        pause_color = (255, 255, 0) # Yellow
        # Draw a 1px line at the very bottom
        bottom_y = chart_height - 1
        draw.line([(0, bottom_y), (chart_width -1, bottom_y)], fill=pause_color, width=1)
        print(f"  Drew yellow line at y={bottom_y}")
        print("-----------------------------")


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
    chart_h = 44
    today = date.today()

    # Ensure data directory exists for testing
    os.makedirs(data_dir, exist_ok=True)
    # You might want to create dummy data files in 'data/' for testing

    # Example usage needs to pass the is_active flag now
    generate_chart(data_dir, output_file, chart_w, chart_h, CATEGORY_COLORS, today, is_active=True) # Example: assume active
    print("Chart generation test finished.")
