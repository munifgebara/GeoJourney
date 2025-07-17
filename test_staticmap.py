from pathlib import Path
from PIL import Image
from analysis.map_generator import generate_map_image
from utils.geo_utils import extract_gps_from_image
import pillow_heif
pillow_heif.register_heif_opener()


if __name__ == "__main__":
    # Caminho da imagem de teste
    img_path = Path("veneza.HEIC")
    gps = extract_gps_from_image(img_path)
    if not gps:
        raise RuntimeError("Não foi possível extrair coordenadas GPS da imagem veneza.heic")
    lat, lon = gps
    print(f"Coordenadas extraídas: lat={lat}, lon={lon}")

    # Redimensiona a imagem para facilitar visualização
    img = Image.open(img_path).convert("RGB")
    img = img.resize((800, 800))

    # Gera o mapa
    map_path = Path("veneza_map.png")
    generate_map_image(lat, lon, map_path, zoom_start=15, size=(200, 200))
    map_img = Image.open(map_path).convert("RGBA")

    # Sobrepõe o mapa no canto inferior direito
    img = img.convert("RGBA")
    img.paste(map_img, (img.width - map_img.width - 10, img.height - map_img.height - 10), map_img)

    # Mostra o resultado
    img.show()
    print("Teste concluído. Imagem exibida na tela.")
