import os
from datetime import datetime, time, date, timedelta, timezone
from PIL import Image, ImageDraw, ImageFont # Import ImageFont

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

    for filename in os.listdir(data_dir):
        if filename.startswith(target_date_str) and filename.endswith(".txt"):
            filepath = os.path.join(data_dir, filename)
            # Extract timestamp from filename
            timestamp_str = filename.split('.')[0]
            dt_obj = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            # Make datetime timezone-aware (assuming local time)
            dt_obj = dt_obj.replace(tzinfo=datetime.now().astimezone().tzinfo)

            with open(filepath, 'r') as f:
                category = f.readline().strip()
                if category: # Ensure category is not empty
                    data_points.append((dt_obj, category))
                # else: # Removed warning for empty category
                #     print(f"Warning: Empty category in file {filename}")

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
    # Debug counters for work time calculation
    debug_total_segments = 0
    debug_work_segments = 0
    debug_work_seconds_by_segment = []
    """Generates the timeline chart image for the target date."""
    print(f"Generating chart for {target_date.isoformat()} (Active: {is_active})...")

    # Define the time range for the chart (7 AM to midnight)
    local_tz = datetime.now().astimezone().tzinfo
    chart_start_dt = datetime.combine(target_date, time(7, 0), tzinfo=local_tz)
    chart_end_dt = datetime.combine(target_date + timedelta(days=1), time(0, 0), tzinfo=local_tz)
    total_duration_seconds = (chart_end_dt - chart_start_dt).total_seconds()

    # Read and sort data points for the target date
    data_points = read_data(data_dir, target_date)

    # Filter points outside the chart's time range
    data_points = [dp for dp in data_points if chart_start_dt <= dp[0] < chart_end_dt]

    print(f"--- Chart Data Points ({len(data_points)}) ---")
    for dt, cat in data_points:
        print(f"  {dt.isoformat()} - {cat}")
    print("--------------------------")

    # Create the image
    unknown_color_tuple = category_colors.get("Unknown", ((211, 211, 211), ""))[0]
    image = Image.new('RGB', (chart_width, chart_height), unknown_color_tuple)
    draw = ImageDraw.Draw(image)

    # Calculate seconds per pixel
    seconds_per_pixel = total_duration_seconds / chart_width
    unknown_color = category_colors.get("Unknown", ((211, 211, 211), ""))[0]

    # Initialize total work time counter
    total_work_seconds = 0

    # Helper to draw a rectangle
    def draw_segment(start_dt, end_dt, color_tuple, category_name):
        nonlocal total_work_seconds, debug_total_segments, debug_work_segments, debug_work_seconds_by_segment
        color = color_tuple[0]
        duration_seconds = (end_dt - start_dt).total_seconds()

        if duration_seconds <= 0:
            return

        start_pixel = int((start_dt - chart_start_dt).total_seconds() / seconds_per_pixel)
        end_pixel = int((end_dt - chart_start_dt).total_seconds() / seconds_per_pixel)

        start_pixel = max(0, start_pixel)
        end_pixel = min(chart_width, end_pixel)

        if end_pixel > start_pixel:
            debug_total_segments += 1
            segment_time_str = f"{int(duration_seconds // 60)}m {int(duration_seconds % 60)}s"
            print(f"  Drawing segment #{debug_total_segments}: Start={start_dt.isoformat()}, End={end_dt.isoformat()}, Duration={segment_time_str}, Category={category_name}, Pixels=[{start_pixel}, {end_pixel}]")
            draw.rectangle([(start_pixel, 0), (end_pixel, chart_height)], fill=color)
            if category_name == "Work":
                debug_work_segments += 1
                total_work_seconds += duration_seconds
                debug_work_seconds_by_segment.append(duration_seconds)
                start_time_str = start_dt.strftime("%H:%M:%S")
                end_time_str = end_dt.strftime("%H:%M:%S")
                print(f"    [WORK] Segment #{debug_total_segments}: {start_time_str} to {end_time_str} - Added {duration_seconds:.2f}s ({segment_time_str}) to Work time. Total: {total_work_seconds:.2f}s")

    # --- Draw intervals ---
    print("--- Drawing Intervals ---")
    current_dt = chart_start_dt

    for i, (event_dt, category) in enumerate(data_points):
        event_dt = max(event_dt, chart_start_dt)
        event_dt = min(event_dt, chart_end_dt)

        if event_dt > current_dt:
            draw_segment(current_dt, event_dt, category_colors["Unknown"], "Unknown (Gap)")
            current_dt = event_dt

        max_valid_end_dt = event_dt + timedelta(seconds=MAX_VALIDITY_SECONDS)
        next_event_start_dt = data_points[i+1][0] if i + 1 < len(data_points) else chart_end_dt
        colored_block_end_dt = min(max_valid_end_dt, next_event_start_dt, chart_end_dt)

        color_desc_tuple = category_colors.get(category, category_colors["Other"])
        draw_segment(current_dt, colored_block_end_dt, color_desc_tuple, category)

        current_dt = colored_block_end_dt

        if current_dt >= chart_end_dt:
            break

    if current_dt < chart_end_dt:
        draw_segment(current_dt, chart_end_dt, category_colors["Unknown"], "Unknown (End Gap)")

    print("-----------------------")

    # --- Draw Hour Ticks ---
    print("--- Drawing Hour Ticks ---")
    tick_color = (255, 255, 255)
    start_hour = chart_start_dt.hour
    end_hour = chart_end_dt.hour

    for hour in range(start_hour, 24):
        tick_dt = datetime.combine(target_date, time(hour, 0), tzinfo=local_tz)

        if tick_dt >= chart_start_dt and tick_dt < chart_end_dt:
            time_offset_seconds = (tick_dt - chart_start_dt).total_seconds()
            tick_x = int(time_offset_seconds / seconds_per_pixel)

            if hour == 9 or hour == 17:
                tick_width = 3
                print(f"  Drawing wide tick at {hour}:00 (x={tick_x})")
                draw.line([(tick_x, 0), (tick_x, chart_height)], fill=tick_color, width=tick_width)
            else:
                tick_width = 1
                print(f"  Drawing tick at {hour}:00 (x={tick_x})")
                draw.line([(tick_x, 0), (tick_x, chart_height)], fill=tick_color, width=tick_width)

    print("------------------------")

    # --- Draw Paused Indicator (if needed) ---
    if not is_active:
        print("--- Drawing Paused Indicator ---")
        pause_color = (255, 255, 0)
        bottom_y = chart_height - 1
        draw.line([(0, bottom_y), (chart_width -1, bottom_y)], fill=pause_color, width=1)
        print(f"  Drew yellow line at y={bottom_y}")
        print("-----------------------------")

    # --- Draw Total Work Time ---
    print("--- Drawing Total Work Time ---")
    # Calculate hours and minutes
    total_work_minutes = int(total_work_seconds // 60)
    work_hours = total_work_minutes // 60
    work_minutes = total_work_minutes % 60
    work_time_str = f"Work: {work_hours}h {work_minutes}m"
    
    # Debug summary of work time calculation
    print(f"\n=== WORK TIME CALCULATION SUMMARY ===")
    print(f"  Total segments drawn: {debug_total_segments}")
    print(f"  Work segments: {debug_work_segments}")
    print(f"  Total work seconds: {total_work_seconds:.2f}s ({total_work_minutes} minutes)")
    print(f"  Formatted work time: {work_time_str}")
    
    if debug_work_segments > 0:
        print(f"\n  Work segments breakdown:")
        work_segment_index = 0
        for i in range(debug_total_segments):
            if i < len(data_points):
                dt, category = data_points[i]
                if category == "Work":
                    work_segment_index += 1
                    seconds = debug_work_seconds_by_segment[work_segment_index-1]
                    minutes = int(seconds // 60)
                    secs = int(seconds % 60)
                    
                    # Calculate end time based on start time and duration
                    start_dt = dt
                    end_dt = start_dt + timedelta(seconds=seconds)
                    
                    start_time_str = start_dt.strftime("%H:%M:%S")
                    end_time_str = end_dt.strftime("%H:%M:%S")
                    
                    print(f"    Segment #{work_segment_index}: {start_time_str} to {end_time_str} - {minutes}m {secs}s ({seconds:.2f}s)")
    
    print(f"=====================================\n")

    # Load a font
    try:
        font = ImageFont.load_default(size=18)
    except AttributeError: # Older PIL might not support size
         font = ImageFont.load_default()
    # Removed OSError handling

    # Text properties
    text_color = (255, 255, 255)
    margin = 5
    bottom_padding = 10 # Padding from the bottom edge

    # Calculate text size and position
    try:
        bbox = draw.textbbox((0, 0), work_time_str, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except AttributeError: # Older PIL might use textsize
         text_width, text_height = draw.textsize(work_time_str, font=font)

    # Position at bottom right
    text_x = chart_width - text_width - margin
    text_y = chart_height - text_height - bottom_padding # Position near the bottom

    # Ensure text doesn't go below the image (shouldn't happen with this calculation, but good practice)
    text_y = max(0, text_y)

    # Draw the text
    draw.text((text_x, text_y), work_time_str, fill=text_color, font=font)
    print(f"  Drew text '{work_time_str}' at ({text_x}, {text_y})")
    print("-----------------------------")

    # Save the image
    image.save(output_path)
    print(f"Chart saved to: {output_path}")

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
    # Removed dummy data creation block

    # Example usage needs to pass the is_active flag now
    generate_chart(data_dir, output_file, chart_w, chart_h, CATEGORY_COLORS, today, is_active=True) # Example: assume active
    print("Chart generation test finished.")
