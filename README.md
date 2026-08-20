# ELEMENTX: AI Gesture Battle

**"Your Hands. Your Power. Your Battle."**

A 2D anime-inspired action-fighting game where every attack, block, dash,
and ultimate is triggered by real-time **hand gestures** read straight
from your webcam — no keyboard or mouse required (though a fallback is
included).

Built entirely with **Python, OpenCV, MediaPipe, Pygame, and NumPy**, with
100% original characters, names, and visuals (no copyrighted assets).

---

## 1. Features

- **Real-time hand-gesture control** via MediaPipe Hands + OpenCV
  - Fist, one/two/three fingers, open palm, thumbs-up, and two-hand
    ultimate are all recognized from landmark geometry
  - Debounced/smoothed classification so gestures don't rapid-fire
  - Live webcam preview with landmark + gesture/confidence overlay
- **Original anime-styled combat** entirely hand-drawn with Pygame
  primitives, gradients, and particle effects — zero external image
  assets required
- **5 elemental abilities**: Basic Punch, Lightning, Wind, Energy
  Blast, and a full-screen Ultimate, each with its own particle FX
- **Combo system**: gesture sequences (e.g. Fist → One Finger → Two
  Fingers) unlock named combos; hit streaks boost damage and score
- **4 enemy archetypes** across **5 levels**, culminating in a
  multi-phase, dodge-capable final boss
- **Full menu flow**: Main Menu → How To Play → Settings → Countdown →
  Playing → Paused → Level Complete → Game Over / Victory
- **Keyboard fallback** — if no webcam is detected, the game
  automatically switches to keyboard controls so it's always playable
- **Modular, typed, documented codebase** split across `vision/`,
  `game/`, `ui/`, and `audio/` packages

---

## 2. Tech Stack

| Purpose                     | Library         |
|------------------------------|-----------------|
| Game engine / rendering / UI | Pygame          |
| Webcam capture & CV effects  | OpenCV          |
| Hand landmark detection      | MediaPipe       |
| Numeric / image processing   | NumPy           |

---

## 3. Installation

### Requirements
- **Python 3.9 – 3.11** (MediaPipe does not yet support the newest
  Python releases on every platform — 3.10 is the safest bet)
- A working webcam (optional — keyboard fallback works without one)
- Windows, macOS, or Linux (primary target: Windows)

### Step-by-step (Windows)

```bat
:: 1. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate

:: 2. Install dependencies
pip install -r requirements.txt

:: 3. Run the game
python main.py
```

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

If `pip install mediapipe` fails on your Python version, install a
slightly older/newer Python (3.10 is recommended) inside the virtual
environment, or check MediaPipe's release notes for the wheel that
matches your platform.

---

## 4. How to Run

```bash
python main.py
```

A `1280x720` window titled **ELEMENTX: AI Gesture Battle** opens on
the Main Menu. Grant camera permission if your OS prompts you.

---

## 5. Camera Requirements

- Any standard USB or built-in webcam works.
- Internally the camera is captured at `640x480` for performance while
  the game window renders at `1280x720`.
- If the webcam can't be opened (missing, denied permission, or in use
  by another app), ELEMENTX detects this automatically and shows:

  > **"Webcam unavailable — Keyboard fallback enabled."**

  and keyboard controls take over immediately — no crash, no restart
  needed.
- You can cycle the camera index from **Settings → Cycle Camera** if
  you have multiple webcams.

---

## 6. Gesture Controls

| Gesture                | Ability            | Effect                          |
|-------------------------|--------------------|----------------------------------|
| ✊ Fist                 | Energy Punch       | Basic attack                     |
| ☝️ One Finger            | Lightning Strike   | Fast, medium-high damage         |
| ✌️ Two Fingers           | Wind Slash         | Area damage                      |
| 🤟 Three Fingers         | Energy Blast       | High damage, high energy cost    |
| 🖐️ Open Palm             | Guardian Shield    | Block incoming damage            |
| 👍 Thumbs Up             | Restore            | Heal a small amount of HP        |
| 🙌 Both Hands Open       | ELEMENTX OMEGA     | Ultimate — needs full energy bar |
| Left hand, move L/R     | Movement           | Moves your character             |

**Combos** (perform gestures in sequence within a few seconds):
- `FIST → ONE FINGER → TWO FINGERS` → **Element Combo**
- `ONE FINGER → THREE FINGERS` → **Lightning Blast Combo**
- `OPEN PALM → FIST` → **Shield Counter**

Landing consecutive hits builds a **COMBO xN** streak that increases
damage and score until it expires from inactivity.

---

## 7. Keyboard Fallback

Used automatically if no webcam/MediaPipe is available, or any time
you just want to test without a camera:

| Key      | Action           |
|----------|------------------|
| `A` / `D`| Move left/right  |
| `J`      | Basic Attack     |
| `K`      | Special Attack (Lightning) |
| `L`      | Ultimate         |
| `SPACE`  | Shield           |
| `ESC`    | Pause            |

---

## 8. Project Architecture

```
elementx/
│
├── main.py                 # Entry point
├── config.py                # All tunable constants (colors, stats, levels...)
├── requirements.txt
├── README.md
│
├── vision/
│   └── gesture_detector.py  # Webcam + MediaPipe -> GestureDetector class
│
├── game/
│   ├── game.py               # GameController: main loop + state machine
│   ├── player.py              # Player entity, animation, HP/energy
│   ├── enemy.py                # Enemy entity + AI (incl. boss phases)
│   ├── level.py                 # Level progression / enemy spawning
│   ├── combat.py                 # Gesture -> ability -> projectile -> damage
│   ├── particles.py               # Reusable particle system + screen FX
│   ├── abilities.py                # Projectiles + ComboTracker
│   ├── collision.py                 # Hit-testing helpers
│   └── states.py                     # GameState enum + StateManager
│
├── ui/
│   ├── menu.py               # Main Menu / How To Play / Settings screens
│   ├── hud.py                  # In-game HUD + webcam preview panel
│   └── buttons.py               # Reusable Button widget
│
├── audio/
│   └── sound_manager.py       # Sound loading/playback with graceful fallback
│
├── assets/
│   ├── images/                 # (unused — all visuals are drawn in code)
│   ├── sounds/                  # Drop .wav/.ogg files here (see its README)
│   └── fonts/
│
└── utils/
    └── helpers.py             # clamp/lerp/draw_text/draw_bar/etc.
```

**Data flow:**
`Webcam → OpenCV → MediaPipe → GestureDetector → GameController → CombatSystem → Player/Enemy/Particles → Pygame render`

---

## 9. Game States

`MAIN_MENU → HOW_TO_PLAY / SETTINGS → COUNTDOWN → PLAYING ⇄ PAUSED →
LEVEL_COMPLETE → (next level) → ... → VICTORY`, with `GAME_OVER`
reachable from `PLAYING` at any time. Managed by
`game/states.py::StateManager`.

---

## 10. Known Limitations

- Gesture classification uses landmark-geometry heuristics rather than
  a trained ML classifier — very unusual hand poses, gloves, or poor
  lighting can reduce accuracy. Adjust **Settings → Gesture
  Sensitivity** and camera position for best results.
- No bundled audio or character sprite assets are shipped (by design,
  to avoid any copyright issues) — all visuals are procedurally drawn
  and all sound hooks are optional no-ops until you add your own files.
- Only one enemy is on-screen at a time (no multi-enemy waves yet).
- Tested primarily on Windows 10/11; camera backend selection
  (`cv2.CAP_DSHOW`) is Windows-specific but falls back gracefully
  elsewhere.

## 11. Future Improvements

- Swap heuristic gesture classification for a small trained gesture
  classifier (e.g. a lightweight MLP on MediaPipe landmarks) for
  higher accuracy across more hand shapes.
- Add multiplayer (local split-camera or online) gesture battles.
- Add more elemental combo chains and a skill-tree/unlock system.
- Sprite-based or skeletal animation option for richer character art.
- Controller/gamepad support alongside gestures and keyboard.

---

## 12. Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` on launch | Run `pip install -r requirements.txt` inside your active virtual environment. |
| Webcam not detected | Check OS camera permissions; try **Settings → Cycle Camera**; the game will fall back to keyboard controls automatically. |
| Low FPS | Close other apps using the camera/GPU; the game already caps camera capture at 640x480 for performance. |
| `mediapipe` fails to install | Use Python 3.9–3.11; some newer Python versions don't have MediaPipe wheels yet. |
| No sound | Expected until you add files to `assets/sounds/` — see `assets/sounds/README.txt`. |
| Gestures feel unresponsive/jumpy | Improve lighting, keep your hand fully in frame, and raise **Gesture Sensitivity** in Settings. |

---

Enjoy the battle — and feel free to fork this into your own portfolio
project, add new elements, bosses, or gesture combos!
