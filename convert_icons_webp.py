"""
Converte ícones PNG e imagens JPG para WebP usando Pillow.
Execute: python convert_icons_webp.py
"""
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Instale o Pillow: pip install Pillow")
    raise

STATIC_IMAGES = Path(__file__).parent / "static" / "images"
ICONS_PNG = [
    "talambralu.png", "rating.png", "cooking-hat.png",
    "green-house.png", "medal.png", "delivery-service.png",
    "share.png", "sale.png", "green-thumb.png",
    "sustainable-agriculture.png", "hand.png", "creative.png",
    "favicon-vida-arroz.png",
]
IMAGES_JPG = [
    "banner-gold.jpg",
    "scenic-view-agricultural-field-against-sky.jpg",
    "closeup-inner-basket-rice-washer-with-tiny-perforations-that-allow-water-flow-through-wash-rice-thoroughly.jpg",
    "white-raw-rice-bowl-with-ear-dark-black-table-background.jpg",
    "close-up-crops-growing-field.jpg",
    "arroz-esquerda.jpg",
    "arroz-direita.jpg",
    "arroz-esquerda-2.jpg",
    "arroz-direita-2.jpg",
    "hands-touching-rice-rice-field.jpg",
    "silhouettes-two-farmers-field-shaking-hands-as-sign-successful-deal.jpg",
]
# Imagens que precisam de qualidade maior (backgrounds em destaque)
IMAGES_JPG_HIGH_QUALITY = [
    "close-up-crops-growing-field.jpg",
    "hands-touching-rice-rice-field.jpg",
]
# Banners: qualidade máxima para evitar pixelação
IMAGES_JPG_QUALITY_100 = [
    "silhouettes-two-farmers-field-shaking-hands-as-sign-successful-deal.jpg",
]


def convert_to_webp(src: Path, dest: Path, quality: int = 90) -> None:
    img = Image.open(src)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGBA")
    else:
        img = img.convert("RGB")
    img.save(dest, "WEBP", quality=quality)


def main():
    for name in ICONS_PNG:
        src = STATIC_IMAGES / name
        if not src.exists():
            print(f"Ignorando (não encontrado): {src}")
            continue
        dest = STATIC_IMAGES / name.replace(".png", ".webp")
        convert_to_webp(src, dest)
        print(f"Convertido: {name} -> {dest.name}")

    for name in IMAGES_JPG:
        src = STATIC_IMAGES / name
        if not src.exists():
            print(f"Ignorando (não encontrado): {src}")
            continue
        dest = STATIC_IMAGES / name.replace(".jpg", ".webp")
        if name in IMAGES_JPG_QUALITY_100:
            quality = 100
        elif name in IMAGES_JPG_HIGH_QUALITY:
            quality = 96
        else:
            quality = 90
        convert_to_webp(src, dest, quality=quality)
        print(f"Convertido: {name} -> {dest.name} (qualidade {quality})")


if __name__ == "__main__":
    main()
