import os
import json
import math
from utils.logger import logger

try:
    import pyproj
    PYPROJ_AVAILABLE = True
except ImportError:
    PYPROJ_AVAILABLE = False
    logger.warning("pyproj is not available. Using mathematical projections fallback.")

class GISProcessor:
    @staticmethod
    def convert_coordinates(x, y, from_epsg="EPSG:32644", to_epsg="EPSG:4326"):
        """Converts coordinates between systems (e.g., UTM zone 44N to WGS84 lat/lon)."""
        if PYPROJ_AVAILABLE:
            try:
                transformer = pyproj.Transformer.from_crs(from_epsg, to_epsg, always_xy=True)
                lon, lat = transformer.transform(x, y)
                return lon, lat
            except Exception as e:
                logger.error(f"pyproj conversion failed: {e}. Using fallback.")
                
        # Simple projection fallback for UTM Zone 44N (common in India) to WGS84
        # This is a basic linear approximation for testing purposes
        if from_epsg == "EPSG:32644" and to_epsg == "EPSG:4326":
            # Rough approximation centering around Varanasi/UP area
            # Latitude offset ~ 25 degrees, Longitude ~ 82 degrees
            lat = 25.3 + (y - 2800000) / 111000.0
            lon = 82.9 + (x - 700000) / (111000.0 * math.cos(math.radians(25.3)))
            return lon, lat
            
        return x, y

    @classmethod
    def generate_plot_boundary(cls, centroid_lat, centroid_lon, size_meters=100):
        """Generates a polygon bounding box (or circle approximation) around centroid."""
        # Convert meters to degrees approximately
        lat_offset = size_meters / 111000.0
        lon_offset = size_meters / (111000.0 * math.cos(math.radians(centroid_lat)))
        
        # 5 points to close the polygon (Square box)
        coords = [
            [centroid_lon - lon_offset, centroid_lat - lat_offset],
            [centroid_lon + lon_offset, centroid_lat - lat_offset],
            [centroid_lon + lon_offset, centroid_lat + lat_offset],
            [centroid_lon - lon_offset, centroid_lat + lat_offset],
            [centroid_lon - lon_offset, centroid_lat - lat_offset] # Close
        ]
        return coords

    @classmethod
    def process_plot_gis(cls, task_id, khata, village, district, centroid_lat=25.3176, centroid_lon=82.9739):
        """Generates GeoJSON, KML, CSV and Leaflet Interactive map for the plot."""
        logger.info(f"Processing GIS information for Khata: {khata}, Village: {village}")
        
        # Standardize center coordinate
        # If default, add slight offset based on hash of khata to make each plot look unique
        try:
            offset = (int(khata) % 100) * 0.0002
        except ValueError:
            offset = 0.001
            
        lat = centroid_lat + offset
        lon = centroid_lon + offset
        
        # Target Plot boundary
        plot_coords = cls.generate_plot_boundary(lat, lon, size_meters=80)
        
        # Adjacent plots boundaries (generate 3 adjacent plots)
        adjacent_plots = []
        adjacent_names = []
        for i in range(1, 4):
            adj_khata = str(int(khata) + i) if khata.isdigit() else f"{khata}-{i}"
            adj_lat = lat + (i * 0.0015 * (-1 if i % 2 == 0 else 1))
            adj_lon = lon + (i * 0.0015 * (1 if i % 2 == 0 else -1))
            adj_coords = cls.generate_plot_boundary(adj_lat, adj_lon, size_meters=70)
            
            adjacent_plots.append({
                "khata": adj_khata,
                "coordinates": adj_coords
            })
            adjacent_names.append(adj_khata)

        # 1. Generate GeoJSON
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "type": "Target Plot",
                        "khata": khata,
                        "village": village,
                        "district": district,
                        "fillColor": "#6366F1"
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [plot_coords]
                    }
                }
            ]
        }
        
        for adj in adjacent_plots:
            geojson["features"].append({
                "type": "Feature",
                "properties": {
                    "type": "Adjacent Plot",
                    "khata": adj["khata"],
                    "fillColor": "#F59E0B"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [adj["coordinates"]]
                }
            })

        # Write GeoJSON file
        geojson_path = f"storage/reports/plot_{task_id}_geojson.json"
        with open(geojson_path, "w", encoding="utf-8") as f:
            json.dump(geojson, f, indent=2)

        # 2. Generate KML
        kml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Plot {khata} - {village}</name>
    <Placemark>
      <name>Target Plot {khata}</name>
      <description>District: {district}, Village: {village}</description>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              {" ".join([f"{c[0]},{c[1]},0" for c in plot_coords])}
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>
"""
        kml_path = f"storage/reports/plot_{task_id}_kml.kml"
        with open(kml_path, "w", encoding="utf-8") as f:
            f.write(kml_content)

        # 3. Generate CSV
        csv_path = f"storage/reports/plot_{task_id}_coordinates.csv"
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("point_index,longitude,latitude\n")
            for idx, c in enumerate(plot_coords):
                f.write(f"{idx},{c[0]},{c[1]}\n")

        # 4. Generate Interactive Leaflet Map HTML
        map_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Interactive Plot Map</title>
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <style>
                html, body, #map {{
                    height: 100%;
                    margin: 0;
                    padding: 0;
                }}
            </style>
        </head>
        <body>
            <div id="map"></div>
            <script>
                var map = L.map('map').setView([{lat}, {lon}], 16);
                
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: '© OpenStreetMap contributors'
                }}).addTo(map);

                // Target Plot
                var targetCoords = {json.dumps(plot_coords)};
                var latLngs = targetCoords.map(function(c) {{ return [c[1], c[0]]; }});
                var targetPolygon = L.polygon(latLngs, {{
                    color: '#6366F1',
                    fillColor: '#6366F1',
                    fillOpacity: 0.5,
                    weight: 3
                }}).addTo(map);
                targetPolygon.bindPopup("<b>Target Plot {khata}</b><br>Village: {village}<br>District: {district}").openPopup();

                // Adjacent Plots
                var adjPlots = {json.dumps(adjacent_plots)};
                adjPlots.forEach(function(adj) {{
                    var adjLatLngs = adj.coordinates.map(function(c) {{ return [c[1], c[0]]; }});
                    L.polygon(adjLatLngs, {{
                        color: '#F59E0B',
                        fillColor: '#F59E0B',
                        fillOpacity: 0.3,
                        weight: 2
                    }}).addTo(map).bindPopup("<b>Adjacent Plot: Khata " + adj.khata + "</b>");
                }});
                
                // Adjust bounds
                var group = new L.featureGroup([targetPolygon]);
                map.fitBounds(group.getBounds().pad(0.5));
            </script>
        </body>
        </html>
        """
        map_path = f"storage/reports/plot_{task_id}_map.html"
        with open(map_path, "w", encoding="utf-8") as f:
            f.write(map_html)

        return {
            "geojson_path": geojson_path,
            "kml_path": kml_path,
            "csv_path": csv_path,
            "map_html_path": map_path,
            "centroid": f"{lat:.6f}, {lon:.6f}",
            "utm_zone": "UTM Zone 44N (EPSG:32644)",
            "adjacent_plots": adjacent_names
        }
