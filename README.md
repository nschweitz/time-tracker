# LLM Time Tracker
Is it still an LLM if you only feed it images? Who knows.

Install dependencies:
```
pip install -r requirements.txt
```

Put your openrouter API key in the right spot:
```
echo my-super-secret-key > api_key.txt
```

And run!
```
python check.py 30
```

30 is the check interval in seconds.

## Screenshot backend
It's set up for wayland so it uses `grim`. If you're on X, edit this line in check.py:

```
    grim_command = ["grim", "-t", "jpeg", "-s", "0.5", image_path]
```

To use `scrot` or whatever X screenshotter you want instead.

## Producing a chart
The program automatically generates a time chart and puts it in /tmp/time.png.
Here's an example:
![](https://github.com/nschweitz/time-tracker/example.png)

## Setting categories
It's hardcoded (sorry) in chart.py:
```
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
```
