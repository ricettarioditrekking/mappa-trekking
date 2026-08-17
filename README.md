# 🗺️ Mappa Percorsi GPX

An interactive topographic map built with Leaflet.js and Python for displaying outdoor hiking and trekking routes. The platform automatically processes `.gpx` track files into a structured `percorsi.geojson` dataset, calculates key trail metrics, applies difficulty ratings, and renders dynamic map controls with custom neon-coded routes.

---

## ✨ Features

* **Topographic Base Layer:** Integrates OpenTopoMap terrain tiles.
* **Dual-Slider Filters:** Filter by Difficulty, Distance (Km min/max), Elevation Gain (+m min/max), Elevation Loss (-m min/max), and Duration Category (*Mezza Giornata* / *Giornata Intera*).
* **High-Visibility Neon Tracks:** Color-coded by difficulty level (*Facile*, *Media*, *Difficile*, *Molto Difficile*) with a custom CSS ambient glow effect.
* **Hybrid Hover/Touch Popups:** Hover preview support on desktop that automatically transitions to tap-and-hold behavior on mobile touch screens.
* **Rich Track Details:** Includes distance, positive/negative elevation, calculated duration, effort score, optional thumbnail image preview, and direct Wikiloc links.

---

## 📁 Repository Structure

```text
.
├── index.html              # Frontend interactive map & sidebar controls
├── elabora_tracce.py       # Python script converting GPX tracks into GeoJSON
├── percorsi.geojson        # Compiled dataset read by index.html
├── README.md               # Project documentation
└── tracce/                 # Subfolder containing GPX files and local images
    ├── sentiero-augusto.gpx
    ├── sentiero-augusto.jpg
    ├── corno-bianco.gpx
    └── corno-bianco.jpg
```

---

## 🔒 Admin Guide: How to Add New Tracks & Images

Everything is fully automated via GitHub Actions—no need to run Python scripts or terminal commands manually!

### 1. Prepare your Files
1. **GPX File:** Export your `.gpx` track file from the device or download it from Wikiloc or similar websites or apps.
2. **Photo (Optional):** Choose a cover photo for the trail popup (`.jpg`, `.jpeg`, or `.png`).
3. **Matching Names:** Make sure both files share the **exact same name**:
   * `tracce/passo-oclini.gpx`
   * `tracce/passo-oclini.jpg`

> **Note:** If no image with a matching name is uploaded, the map will simply omit the thumbnail from the popup without causing errors.

### 2. Upload to GitHub
Upload or commit the new `.gpx` and image files directly into the `tracce/` folder on GitHub (via web browser or `git push`).

### 3. Automatic Deployment
Once pushed, GitHub Actions automatically runs the script, updates `percorsi.geojson`, and publishes the changes to your live site within a couple of minutes.
