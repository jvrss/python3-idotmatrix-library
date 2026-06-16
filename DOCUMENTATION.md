# iDotMatrix Python Library — Documentation
A Python library to control **iDotMatrix pixel displays** (16×16, 32×32, or 64×64) via **Bluetooth**, without needing the official iDotMatrix mobile app.
---
## Table of Contents
- [Installation](#installation)
- [Connection](#connection)
- [Modules](#modules)
  - [Clock](#clock)
  - [Chronograph](#chronograph)
  - [Countdown](#countdown)
  - [Fullscreen Color](#fullscreen-color)
  - [Image](#image)
  - [GIF](#gif)
  - [Text](#text)
  - [Scoreboard](#scoreboard)
  - [Effect](#effect)
  - [System](#system)
  - [Common](#common)
- [Known Issues & 64x64 Display Notes](#known-issues--6464-display-notes)
- [Not Yet Fully Implemented](#not-yet-fully-implemented)
- [Dependencies](#dependencies)
---
## Installation
### From PyPI (recommended)
\`\`\`bash
pip install idotmatrix
\`\`\`
### From source
\`\`\`bash
git clone https://github.com/derkalle4/python3-idotmatrix-library.git
cd python3-idotmatrix-library
pip install .
\`\`\`
---
## Connection
Before using any module, initialize and connect to your device using \`ConnectionManager\`.  
It uses the [bleak](https://github.com/hbldh/bleak) library under the hood to communicate over Bluetooth.
\`\`\`python
import asyncio
from idotmatrix import ConnectionManager
async def main():
    conn = ConnectionManager()
    await conn.connectBySearch()  # automatically finds and connects to the first iDotMatrix device
asyncio.run(main())
\`\`\`
You can also connect by MAC address directly:
\`\`\`python
await conn.connectByAddress("XX:XX:XX:XX:XX:XX")
\`\`\`
> **Note:** If you skip the connection step, all module methods will return the raw \`bytearray\` command instead of sending it. This lets you use your own Bluetooth implementation.
---
## Modules
### Clock
Display a clock on the screen. Supports 8 visual styles (0–7), 12h/24h format, optional date display, and custom RGB color.
\`\`\`python
from idotmatrix import Clock
clock = Clock()
await clock.setMode(
    style=2,
    visibleDate=True,
    hour24=True,
    r=255, g=255, b=255
)
\`\`\`
| Parameter     | Type  | Default | Description                        |
|---------------|-------|---------|------------------------------------|
| \`style\`       | int   | —       | Clock style (0 to 7)               |
| \`visibleDate\` | bool  | \`True\`  | Show or hide the date              |
| \`hour24\`      | bool  | \`True\`  | 24h (\`True\`) or 12h (\`False\`) mode |
| \`r\`           | int   | \`255\`   | Red component (0–255)              |
| \`g\`           | int   | \`255\`   | Green component (0–255)            |
| \`b\`           | int   | \`255\`   | Blue component (0–255)             |
---
### Chronograph
Control a stopwatch on the display.
\`\`\`python
from idotmatrix import Chronograph
chrono = Chronograph()
await chrono.setMode(1)  # start
\`\`\`
| Mode | Description          |
|------|----------------------|
| \`0\`  | Reset                |
| \`1\`  | Start / Restart      |
| \`2\`  | Pause                |
| \`3\`  | Continue after pause |
> **Tip:** Always use mode \`1\` first to properly initialize the chronograph on the device.
---
### Countdown
Set and control a countdown timer with minutes and seconds.
\`\`\`python
from idotmatrix import Countdown
cd = Countdown()
await cd.setMode(mode=1, minutes=5, seconds=30)
\`\`\`
| Parameter | Type | Description                                      |
|-----------|------|--------------------------------------------------|
| \`mode\`    | int  | \`0\`=disable, \`1\`=start, \`2\`=pause, \`3\`=restart   |
| \`minutes\` | int  | Minutes to count down from                       |
| \`seconds\` | int  | Seconds to count down from (0–59)                |
---
### Fullscreen Color
Fill the entire display with a solid RGB color.
\`\`\`python
from idotmatrix import FullscreenColor
fc = FullscreenColor()
await fc.setMode(r=0, g=255, b=128)
\`\`\`
| Parameter | Type | Default | Description             |
|-----------|------|---------|-------------------------|
| \`r\`       | int  | \`0\`     | Red component (0–255)   |
| \`g\`       | int  | \`0\`     | Green component (0–255) |
| \`b\`       | int  | \`0\`     | Blue component (0–255)  |
---
### Image
Upload a static PNG image to the display. The image can be resized automatically to fit the device's pixel grid.
#### Upload with automatic resize (recommended)
\`\`\`python
from idotmatrix import Image
img = Image()
await img.uploadProcessed("my_image.png", pixel_size=64)
\`\`\`
#### Upload without processing
\`\`\`python
await img.uploadUnprocessed("my_image.png")
\`\`\`
#### Enable / Disable DIY draw mode
\`\`\`python
await img.setMode(1)  # 0=disable, 1=enable
\`\`\`
| Parameter    | Type | Default | Description                                                                                 |
|--------------|------|---------|---------------------------------------------------------------------------------------------|
| \`file_path\`  | str  | —       | Path to the PNG file                                                                        |
| \`pixel_size\` | int  | \`32\`    | Physical resolution of your display — use \`16\` for 16x16, \`32\` for 32x32, \`64\` for 64x64  |
> **About \`pixel_size\`:** This tells the library the actual pixel grid size of your device.  
> \`uploadProcessed()\` resizes your image to exactly \`pixel_size x pixel_size\` before sending it.  
> For example, a 500x500 PNG sent to a 64x64 display will be resized to 64x64 automatically.  
> Using the wrong size will result in a stretched or cropped image on the display.  
> \`uploadUnprocessed()\` skips all resizing and sends the file as-is.
---
### GIF
Upload an animated GIF to the display. Each frame is resized automatically to fit the device's pixel grid.
#### Upload with automatic resize (recommended)
\`\`\`python
from idotmatrix import Gif
gif = Gif()
await gif.uploadProcessed("animation.gif", pixel_size=64)
\`\`\`
#### Upload without processing
\`\`\`python
await gif.uploadUnprocessed("animation.gif")
\`\`\`
| Parameter    | Type | Default | Description                                                                                 |
|--------------|------|---------|---------------------------------------------------------------------------------------------|
| \`file_path\`  | str  | —       | Path to the GIF file                                                                        |
| \`pixel_size\` | int  | \`32\`    | Physical resolution of your display — use \`16\` for 16x16, \`32\` for 32x32, \`64\` for 64x64  |
> **About \`pixel_size\`:** Same as with images — every frame of the GIF will be individually  
> resized to \`pixel_size x pixel_size\` before being re-encoded and uploaded.  
> A 200x200 GIF with 10 frames sent to a 64x64 display will have each frame resized to 64x64.
---
### Text
Scroll or animate text on the display. Supports multiple animation modes, custom font, text color, and background color.
> **Important for 64x64 displays:** Pass \`display_size=64\` when creating the \`Text\` instance.  
> This is required so character bitmaps are rendered at the correct resolution (32x64 px per character).  
> Without this, text will appear too small on the display.  
> The internal separator byte for 64x64 is not yet officially reverse-engineered — consider this **experimental**.
\`\`\`python
from idotmatrix import Text
text = Text(display_size=64)  # use 16, 32, or 64 to match your device
await text.setMode(
    text="Hello!",
    font_size=32,
    text_mode=1,
    speed=95,
    text_color_mode=1,
    text_color=(255, 255, 0),
    text_bg_mode=0,
    text_bg_color=(0, 0, 0),
)
\`\`\`
#### \`display_size\` — character bitmap mapping
| \`display_size\` | Char bitmap size | Separator byte | Status           |
|----------------|-----------------|----------------|------------------|
| \`16\`           | 8 x 16 px       | \`0x02\`         | Confirmed        |
| \`32\`           | 16 x 32 px      | \`0x05\`         | Confirmed        |
| \`64\`           | 32 x 64 px      | \`0x05\` (guess) | Experimental     |
#### \`text_mode\` values
| Value | Description               |
|-------|---------------------------|
| \`0\`   | Static (replace text)     |
| \`1\`   | Marquee (left scroll)     |
| \`2\`   | Reversed marquee          |
| \`3\`   | Vertical rising marquee   |
| \`4\`   | Vertical lowering marquee |
| \`5\`   | Blinking                  |
| \`6\`   | Fading                    |
| \`7\`   | Tetris                    |
| \`8\`   | Filling                   |
#### \`text_color_mode\` values
| Value | Description      |
|-------|------------------|
| \`0\`   | White            |
| \`1\`   | Custom RGB color |
| \`2–5\` | Rainbow modes    |
#### \`text_bg_mode\` values
| Value | Description           |
|-------|-----------------------|
| \`0\`   | Black background      |
| \`1\`   | Custom RGB background |
> **Note:** A custom font can be provided via \`font_path\`. By default, the library uses the bundled \`Rain-DRM3.otf\` font from the \`fonts/\` folder.
---
### Scoreboard
Display a scoreboard with two counters (0–999).
\`\`\`python
from idotmatrix import Scoreboard
sb = Scoreboard()
await sb.setMode(count1=3, count2=1)
\`\`\`
| Parameter | Type | Description           |
|-----------|------|-----------------------|
| \`count1\`  | int  | First score (0–999)   |
| \`count2\`  | int  | Second score (0–999)  |
---
### Effect
Apply animated visual effects to the display. Choose from 7 built-in styles with customizable colors.
\`\`\`python
from idotmatrix import Effect
effect = Effect()
await effect.setMode(
    style=0,
    rgb_values=[(255, 0, 0), (0, 0, 255), (0, 255, 0)]  # 2 to 7 color tuples
)
\`\`\`
#### \`style\` values
| Value | Description                                |
|-------|--------------------------------------------|
| \`0\`   | Graduated horizontal rainbow               |
| \`1\`   | Random colored pixels on black             |
| \`2\`   | Random white pixels on changing background |
| \`3\`   | Vertical rainbow                           |
| \`4\`   | Diagonal right rainbow                     |
| \`5\`   | Diagonal left rainbow on black background  |
| \`6\`   | Random colored pixels                      |
| Parameter    | Type                    | Description                     |
|--------------|-------------------------|---------------------------------|
| \`style\`      | int                     | Effect style (0–6)              |
| \`rgb_values\` | list of (int, int, int) | List of 2 to 7 RGB color tuples |
---
### System
Low-level system commands for device management.
\`\`\`python
from idotmatrix import System
sys = System()
await sys.deleteDeviceData()  # reset device to factory defaults
\`\`\`
> **Note:** \`getDeviceLocation()\` is also available but not yet fully functional — it requires AES encryption matching the iDotMatrix app's implementation.
---
### Common
Utility commands for general device control.
\`\`\`python
from idotmatrix import Common
common = Common()
await common.screenOn()                       # turn screen on
await common.screenOff()                      # turn screen off
await common.setBrightness(80)                # set brightness (5–100%)
await common.flipScreen(True)                 # rotate 180 degrees
await common.setTime(2026, 6, 15, 14, 30, 0) # sync device clock
await common.reset()                          # reset device internals
await common.setPassword(123456)              # set 6-digit Bluetooth password
await common.freezeScreen()                   # freeze/unfreeze current screen
\`\`\`
---
## Known Issues & 64x64 Display Notes
| Module    | Issue                                                                                             | Status          |
|-----------|---------------------------------------------------------------------------------------------------|-----------------|
| \`Image\`   | Works with \`pixel_size=64\`. No known bugs.                                                        | Supported       |
| \`Gif\`     | Works with \`pixel_size=64\`. No known bugs.                                                        | Supported       |
| \`Text\`    | Requires \`Text(display_size=64)\`. Separator byte for 64x64 is not officially reverse-engineered. | Experimental    |
| \`Clock\`   | Protocol bytes not verified for 64x64 displays — may work but is untested.                        | Untested        |
| \`Effect\`  | Protocol bytes not verified for 64x64 displays — may work but is untested.                        | Untested        |
---
## Not Yet Fully Implemented
The following modules exist in the library but are not yet fully reverse-engineered:
| Module      | Status                |
|-------------|-----------------------|
| \`MusicSync\` | Not implemented       |
| \`Graffiti\`  | Partially implemented |
| \`Eco\`       | Partially implemented |
Other missing features:
- Alarm & Buzzer support
- Cloud API for downloading/uploading images
- Bluetooth password protection
- Parsing device response byte arrays
---
## Dependencies
| Package        | Purpose                            |
|----------------|------------------------------------|
| \`bleak\`        | Bluetooth Low Energy communication |
| \`pillow\`       | Image and GIF processing           |
| \`cryptography\` | AES encryption (System module)     |
\`\`\`bash
pip install bleak pillow cryptography
\`\`\`
---
## License
Distributed under the **GNU General Public License**. See [LICENSE](LICENSE) for more information.
