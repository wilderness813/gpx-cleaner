# 🧹 GPX Cleaner

**Clean your GPX tracks from GPS spoofing and jamming artifacts**

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-app-url.streamlit.app)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

---

## 📌 Overview

**GPX Cleaner** is a web-based tool that removes GPS spoofing and jamming artifacts from GPX files.

In areas affected by GPS interference (e.g., Russia, Ukraine, Middle East, and other conflict zones), your GPS device may suddenly jump hundreds of kilometers away due to:

- **GPS spoofing** — fake signals that trick your device into showing incorrect coordinates
- **GPS jamming** — signal disruption that causes erratic position jumps
- **Signal reflection** — urban canyons and dense buildings that distort GPS readings

Your Strava, Garmin, or other fitness trackers record these jumps as impossibly fast movements, ruining your stats with:

- Inflated distances (e.g., 50 km instead of 5 km)
- Absurd average speeds (e.g., 300 km/h while walking)
- Broken maps with disconnected segments
- Invalid personal records

**GPX Cleaner** solves this by automatically detecting parallel trajectories in your GPX file, showing each as a separate "ride," and letting you pick the real one.

---

## ✨ Features

- **🔍 Automatic Cluster Detection** — finds all parallel routes in your GPX file
- **📊 Detailed Statistics** — shows distance, time, speed, and point count for each cluster
- **📍 Geographic Labels** — identifies locations (e.g., "Kyiv", "Moscow", "Ostrova Karedzhi")
- **🔄 Smart Interpolation** — fills gaps between good points (linear or via OSRM)
- **🗺️ OSRM Integration** — uses OpenStreetMap to create realistic routes along roads
- **💾 One-Click Export** — download the cleaned track as a GPX file

---

## 🚀 Quick Start

### Option 1: Use the Web App (Recommended)

1. Open the live app: [https://gpx-cleaner.streamlit.app](https://gpx-cleaner.streamlit.app)
2. Upload your GPX file (you can download it from [the Garmin Connect website](https://connect.garmin.com))
3. Review the detected clusters
4. Select the correct one
5. Download the cleaned GPX
6. You can delete the original event and upload the modified event on https://connect.garmin.com.

### Option 2: Run Locally

```bash
# Clone the repository
git clone https://github.com/wilderness813/gpx-cleaner.git
cd gpx-cleaner

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

Then open `http://localhost:8501` in your browser.

---

## 🛠️ How It Works

### 1. Dynamic Clustering

The algorithm processes your GPX file point by point:

- Starts with the first point as a new "cluster" (trajectory)
- For each next point, checks if it's within a reasonable distance from the **last known point** of any existing cluster
- The reasonable distance grows over time based on `MAX_SPEED_KMH` (e.g., if you haven't moved in 10 minutes, the radius expands to allow a 5 km jump at 30 km/h)
- If a point doesn't match any existing cluster, it starts a **new cluster**
- Old clusters that haven't received new points for `MAX_WAIT_MINUTES` are frozen (but can wake up if GPS returns)

### 2. Cluster Selection

**Mode 1: Manual Selection (Interactive)**

The app shows all clusters with:
- 📍 Geographic location (e.g., "Kyiv center", "Ostrova Karedzhi")
- 📏 Total distance
- ⏱️ Duration
- 🚴 Average speed
- 📌 Number of points

You choose which cluster is your real track.

**Mode 2: Automatic Selection**

The app automatically selects the cluster with the **most points** (the longest ride).

### 3. Interpolation

After selecting the main cluster:

- Detects gaps between consecutive points
- If the gap exceeds the maximum possible distance at `MAX_SPEED_KMH`, fills it with interpolated points
- Optionally uses OSRM to route along real roads (instead of straight lines)

---

## 📊 Example

**Before (Raw GPX):**

```
Points: 1,245
Distance: 47.3 km
Avg Speed: 32.1 km/h
```

*Reality: You walked 5 km at 5 km/h, GPS spoofing added 42.3 km of jumps.*

**After (Cleaned):**

```
Points: 1,180
Distance: 5.2 km
Avg Speed: 4.8 km/h
```

*Your real track is restored.*

---

## ⚙️ Configuration

Edit these variables at the top of `app.py`:

```python
MAX_SPEED_KMH = 35.0          # Max reasonable speed (km/h)
MAX_WAIT_MINUTES = 10         # Minutes before freezing a cluster
INTERPOLATE = True            # Enable gap interpolation
USE_OSRM = True               # Use OSRM for realistic routing
OSRM_PROFILE = 'bike'         # 'foot' | 'bike' | 'car'
MAX_GAP_M = 500.0             # Max gap between cluster points (meters)
MIN_CLUSTER_POINTS = 3        # Minimum points to consider a cluster valid
```

---

## 📂 File Structure

```
gps-cleaner/
├── app.py                 # Main application
├── requirements.txt       # Dependencies
├── README.md             # This file
└── .gitignore            # Git ignore rules
```

---

## 🧪 Dependencies

- [Streamlit](https://streamlit.io/) — Web UI framework
- [Requests](https://docs.python-requests.org/) — HTTP client for OSRM API

Install all with:

```bash
pip install streamlit requests
```

---

## 🌐 OSRM Integration

The app can use [OSRM (Open Source Routing Machine)](http://project-osrm.org/) for realistic interpolation:

- **Public API**: `http://router.project-osrm.org/route/v1/` (free, rate-limited)
- **Profiles**: `foot` (walking), `bike` (cycling), `car` (driving)
- **Fallback**: If OSRM fails, falls back to linear interpolation

To use a self-hosted OSRM instance, change `OSRM_URL` in the config.

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. Fork the repository
2. Create a new branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Commit them (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

---

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.

---

## 🙏 Acknowledgments

- [OSRM](http://project-osrm.org/) for open-source routing
- [OpenStreetMap](https://www.openstreetmap.org/) for map data
- [Streamlit](https://streamlit.io/) for making data apps so easy

---

## 📧 Contact

Ruslan Morozov — mir4595@yandex.ru | sneg.taet.v.aprele@gmail.com

Project Link: [https://github.com/wilderness813/gpx-cleaner](https://github.com/wilderness813/gpx-cleaner)

---

## ⭐ Support

If you find this useful, please give it a ⭐ on GitHub!

---

## ❓ FAQ

**Q: Does this work for any GPX file?**

A: Yes, any GPX file with `trkpt` elements and optional time tags.

**Q: What if my GPX has no time data?**

A: The app works without time data but falls back to simpler distance-based clustering.

**Q: Is my data uploaded anywhere?**

A: No! Everything runs locally in your browser via Streamlit. No files are sent to any server.

**Q: Why does GPS spoofing happen?**

A: In conflict zones, GPS jamming and spoofing are used as electronic warfare. Civilian GPS devices receive fake signals that cause incorrect positioning.

**Q: What's the difference between jamming and spoofing?**

A: **Jamming** blocks the GPS signal, causing position loss or jumps. **Spoofing** sends fake signals, making your device believe it's somewhere else entirely.

**Q: Can I use this offline?**

A: Yes! Run it locally on your machine. The OSRM integration requires internet for routing, but you can disable it.

---

**Made with ❤️ for everyone whose Strava stats got wrecked by GPS spoofing.**
