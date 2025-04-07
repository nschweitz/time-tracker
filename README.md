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

To use `scrot` or whatever X screenshotter you want instead. The format
shouldn't matter, I just used jpeg since it's smaller. The `-s 0.5` scales it
down to 50%, which is still readable for the LLM but saves some money.

## Producing a chart
The program automatically generates a time chart and puts it in /tmp/time.png.
Here's an example:
![epic sreenie](https://github.com/nschweitz/time-tracker/blob/e120f8dc6223c049165ff3e7724cae6dc1ca85d9/example.png)

A work of art it is not. But it works, the vertical lines are the hours of the
day from 7 AM to midnight, and then the colored strips are whatever I was doing
at that time. Light blue is work, orange is youtube & co, and so on. As you can
see the tool was disabled for most of the day, mostly because it hadn't been
written yet ;-)

### Why is it so hideous?
So it fits in my bar.

![full screenshot]()

## Pause and unpause

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

Go edit it. The key is the category name, then the color in RGB, and then a
description of the category that gets fed to the LLM.

## Your code sucks balls
It's actually Gemini's spaghetti code, thank you very much.
