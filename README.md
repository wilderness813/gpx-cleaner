# 🧹 GPX Cleaner

**Remove GPS spoofing and jamming artifacts from your GPX tracks**

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://wilderness813.streamlit.app)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🎯 Use Case

In areas affected by GPS jamming or spoofing (e.g., Ukraine, Russia, Middle East, and other conflict zones), your GPS device may suddenly jump hundreds of kilometers away. Your Strava, Garmin, or other fitness trackers record these jumps as impossibly fast movements, ruining your stats with inflated distances, absurd speeds, and broken maps.

**GPX Cleaner** detects parallel trajectories in your GPX file, shows each as a separate "ride," and lets you pick the real one.

---

## 🚀 How to Use

1. **Upload** your GPX file from Garmin Connect, Strava, or your GPS device
2. **Review** the detected clusters — the largest one is usually your real track
3. **Adjust** advanced settings if needed (max speed, loop route)
4. **Select** the correct cluster and click **Process**
5. **Download** the cleaned GPX file
6. **Upload** back to Garmin Connect, Strava, or your preferred platform

---

## ⚙️ How It Works

1. **Dynamic Clustering** — groups points into parallel trajectories based on time and distance
2. **Endpoint Fixing** — if you enable "loop route," fixes start/end points using the good endpoint as reference
3. **Interpolation** — fills gaps between good points using linear interpolation or OSRM (OpenStreetMap routing)
4. **Export** — saves the selected cluster as a clean GPX file

---

## 🛠️ Tech Stack

- Python + Streamlit (web UI)
- OSRM (OpenStreetMap routing)
- Nominatim (reverse geocoding)

---

## 📄 License

MIT License — free for personal and commercial use.
