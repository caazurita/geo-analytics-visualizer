# Geo Analytics Visualizer

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.59-FF4B4B?logo=streamlit)](https://streamlit.io)
[![Kepler.gl](https://img.shields.io/badge/Kepler.gl-0.3-009EE6?logo=uber)](https://kepler.gl)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

An interactive web application for visualizing and analyzing GPS trajectories and GeoJSON geospatial data. Built with Streamlit and Kepler.gl.

![Screenshot](https://via.placeholder.com/800x450?text=Geo+Analytics+Visualizer)

## Features

- **File upload** — Upload GPS files in CSV, JSON, or GeoJSON format (Point, LineString, Polygon, and Multi* variants)
- **Demo datasets** — Explore instantly with built-in sample data (points and routes)
- **Interactive map** — GPS routes rendered as lines, points, or polygons on a Kepler.gl map with automatic zoom-to-fit
- **Summary statistics** — Point count, feature count, total distance, average speed, and polygon area estimates
- **Filters** — Filter by device/feature ID, date range, or time of day
- **Charts** — Speed, altitude, segment distance, and cumulative distance over time; feature distribution breakdown
- **Raw data preview** — Inspect the underlying parsed data in a sortable table

## Installation

### Prerequisites

- Python 3.10+
- [conda](https://docs.conda.io/) or [pip](https://pip.pypa.io/)

### Setup

```bash
# Clone the repository
git clone https://github.com/your-username/geo-analytics-visualizer.git
cd geo-analytics-visualizer

# Create and activate a conda environment (recommended)
conda create -n geo-analytics python=3.11
conda activate geo-analytics

# Install dependencies
pip install streamlit keplergl streamlit-keplergl pandas geopandas plotly geopy numpy
```

## Usage

```bash
streamlit run app.py
```

Open the URL shown in the terminal (typically `http://localhost:8501`).

### Loading data

| Method | Description |
|---|---|
| **Upload** | Drag & drop a CSV, JSON, or GeoJSON file onto the uploader |
| **Demo data** | Click *Load demo: Points* or *Load demo: Routes* to explore sample datasets |

### Supported data formats

**CSV**
```csv
latitude,longitude,timestamp,device_id,speed,altitude
40.7128,-74.0060,2025-01-01 10:00:00,dev_1,45.2,100
```

**GeoJSON (Point, LineString & Polygon)**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "Point", "coordinates": [-74.0060, 40.7128] },
      "properties": { "id": "point_1", "speed": 45.2 }
    },
    {
      "type": "Feature",
      "geometry": {
        "type": "LineString",
        "coordinates": [[-74.0060, 40.7128], [-74.0055, 40.7135]]
      },
      "properties": { "id": "route_1" }
    }
  ]
}
```

Coordinates must follow the GeoJSON standard: `[longitude, latitude]`.

## Project structure

```
geo-analytics-visualizer/
├── app.py              # Main Streamlit application
├── data/
│   ├── geojson_output_points.json   # Demo: point features
│   ├── geojson_output_lines.json    # Demo: route features
│   └── FrequentRoutes.json
├── requirements.txt    # (optional) pinned dependencies
├── .gitignore
└── README.md
```

## Tech stack

| Technology | Purpose |
|---|---|
| [Streamlit](https://streamlit.io) | Web UI framework |
| [Kepler.gl](https://kepler.gl) | Geospatial map visualization |
| [Pandas](https://pandas.pydata.org) | Data manipulation |
| [GeoPandas](https://geopandas.org) | Geospatial data handling |
| [Shapely](https://shapely.readthedocs.io) | Geometry operations |
| [Plotly](https://plotly.com/python) | Charts & graphs |
| [GeoPy](https://geopy.readthedocs.io) | Distance calculations |

## License

[MIT](LICENSE)
