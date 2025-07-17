# map_generator.py
from pathlib import Path
from staticmap import StaticMap, CircleMarker

def generate_map_image(lat: float, lon: float, output_path: Path, zoom_start: int = 15, size: tuple = (200, 200)):
    """
    Gera um PNG de mapa centrado em (lat, lon) com marcador e salva em output_path.
    Usa staticmap (OpenStreetMap) sem depender de API externa.
    """
    # staticmap espera (lon, lat)
    map_obj = StaticMap(size[0], size[1], url_template='https://a.tile.openstreetmap.org/{z}/{x}/{y}.png')
    marker = CircleMarker((lon, lat), 'red', 10)
    map_obj.add_marker(marker)
    # O zoom 15 é mais próximo do padrão de visualização urbana
    image = map_obj.render(zoom=zoom_start, center=(lon, lat))
    image.save(str(output_path))