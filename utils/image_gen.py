"""
Premium Welcome Card Generator
===============================
Professional anime-style welcome cards with:
- Left-side shadow overlays (keeps right side bright)
- Glow effects & Premium double borders
- Profile picture with name styled directly below
- Custom fonts support with fallback
- Advanced text effects & decorations
"""

import io
import os
import logging
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter, ImageEnhance

# Configure logging
logger = logging.getLogger(__name__)

# ==================== CONSTANTS ====================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# Default image settings
DEFAULT_BG_WIDTH = 800
DEFAULT_BG_HEIGHT = 400
DEFAULT_PFP_SIZE = 170
DEFAULT_BORDER_WIDTH = 6
DEFAULT_FONT_SIZE = 34


# ==================== COLOR HELPERS ====================
def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


# ==================== FONT LOADER ====================
class FontLoader:
    """Professional font loader with multiple fallbacks."""
    
    # Priority list of fonts to try (cross-platform)
    FONT_PATHS = {
        'bold': [
            os.path.join(ASSETS_DIR, "Poppins-Bold.ttf"),
            "/usr/share/fonts/truetype/poppins/Poppins-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "C:\\Windows\\Fonts\\arialbd.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "arialbd.ttf",
        ],
        'medium': [
            os.path.join(ASSETS_DIR, "Poppins-Medium.ttf"),
            "/usr/share/fonts/truetype/poppins/Poppins-Medium.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "C:\\Windows\\Fonts\\arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "arial.ttf",
        ]
    }
    
    @classmethod
    def load(cls, size: int = 32, style: str = 'bold') -> ImageFont.FreeTypeFont:
        """Load font with multiple fallback options."""
        paths = cls.FONT_PATHS.get(style, cls.FONT_PATHS['bold'])
        
        for path in paths:
            try:
                if os.path.exists(path):
                    font = ImageFont.truetype(path, size)
                    logger.debug(f"Loaded font: {path}")
                    return font
            except Exception as e:
                logger.debug(f"Font load failed for {path}: {e}")
                continue
        
        # Final fallback to default font
        logger.warning("No custom font found, using default")
        return ImageFont.load_default()


# ==================== IMAGE PROCESSOR ====================
class ImageProcessor:
    """Advanced image processing utilities."""
    
    @staticmethod
    def create_left_shadow_overlay(
        size: Tuple[int, int],
        fade_distance: int = 500
    ) -> Image.Image:
        """Create a gradient overlay that only shadows the left side."""
        width, height = size
        overlay = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        for x in range(fade_distance):
            # 240 is max opacity (dark), fading to 0 (transparent) by fade_distance
            alpha = max(0, int(240 - (240 * (x / fade_distance))))
            # A slight dark-purple tint that looks premium with anime backgrounds
            draw.line([(x, 0), (x, height)], fill=(20, 10, 30, alpha))
            
        return overlay

    @staticmethod
    def add_vignette(
        image: Image.Image,
        intensity: float = 0.2
    ) -> Image.Image:
        """Add a subtle vignette effect to the edges."""
        width, height = image.size
        vignette = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(vignette)
        
        center_x, center_y = width // 2, height // 2
        max_dist = (center_x ** 2 + center_y ** 2) ** 0.5
        
        for y in range(height):
            for x in range(width):
                dist = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
                alpha = int(255 * (dist / max_dist) * intensity)
                vignette.putpixel((x, y), (0, 0, 0, alpha))
        
        return Image.alpha_composite(image, vignette)


# ==================== WELCOME CARD GENERATOR ====================
class WelcomeCardGenerator:
    """
    Premium welcome card generator.
    """
    
    # Predefined color themes
    THEMES = {
        'gold': {
            'primary': '#FFD700',
            'secondary': '#FFFFFF',
            'glow': '#FFA500',
        }
    }
    
    def __init__(
        self,
        bg_path: Optional[str] = None,
        width: int = DEFAULT_BG_WIDTH,
        height: int = DEFAULT_BG_HEIGHT,
        theme: str = 'gold'
    ):
        self.width = width
        self.height = height
        self.theme = self.THEMES.get(theme, self.THEMES['gold'])
        self.bg_path = bg_path or os.path.join(ASSETS_DIR, "anime_bg.jpg")
        
    def load_background(self) -> Image.Image:
        """Load and prepare background image."""
        try:
            if os.path.exists(self.bg_path):
                bg = Image.open(self.bg_path).convert("RGBA")
                bg = ImageOps.fit(bg, (self.width, self.height), centering=(0.5, 0.5))
                logger.debug(f"Background loaded: {self.bg_path}")
                return bg
        except Exception as e:
            logger.warning(f"Failed to load background: {e}")
        
        # Fallback dark background
        return Image.new("RGBA", (self.width, self.height), (25, 25, 30, 255))
    
    def create_pfp_mask(self, size: int = DEFAULT_PFP_SIZE) -> Image.Image:
        """Create a circular mask for profile picture."""
        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)
        return mask
    
    def draw_premium_border(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        size: int,
        border_width: int = DEFAULT_BORDER_WIDTH
    ) -> None:
        """Draw premium double border (Gold + White)."""
        primary = self.theme['primary']
        secondary = self.theme['secondary']
        
        # Outer Gold Border
        outer = border_width + 2
        draw.ellipse(
            (x - outer, y - outer, x + size + outer, y + size + outer),
            fill=primary
        )
        
        # Inner White Border gap
        inner = 3
        draw.ellipse(
            (x - inner, y - inner, x + size + inner, y + size + inner),
            fill=secondary
        )
    
    def draw_username(
        self,
        draw: ImageDraw.ImageDraw,
        name: str,
        center_x: int,
        y: int,
        font_size: int = DEFAULT_FONT_SIZE
    ) -> None:
        """Draw username with heavy professional drop shadow directly below PFP."""
        font = FontLoader.load(font_size, 'bold')
        
        # Truncate name if too long to keep image clean
        display_name = name[:14] + ".." if len(name) > 14 else name
        
        text_bbox = draw.textbbox((0, 0), display_name, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_x = center_x - (text_width // 2)
        
        # Mast dimensions/shadow (Black shadow for pop effect)
        shadow_offset = 3
        draw.text(
            (text_x + shadow_offset, y + shadow_offset),
            display_name,
            font=font,
            fill=(0, 0, 0, 220)
        )
        
        # Main text (White for pure contrast)
        draw.text(
            (text_x, y),
            display_name,
            font=font,
            fill="#FFFFFF"
        )
    
    def draw_subtitle(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        center_x: int,
        y: int,
        font_size: int = 18
    ) -> None:
        """Draw small subtitle below the name."""
        font = FontLoader.load(font_size, 'medium')
        
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_x = center_x - (text_width // 2)
        
        # Shadow
        draw.text((text_x + 2, y + 2), text, font=font, fill=(0, 0, 0, 200))
        # Main text (Gold)
        draw.text((text_x, y), text, font=font, fill=self.theme['primary'])

    def draw_decorations(self, draw: ImageDraw.ImageDraw) -> None:
        """Draw subtle sparkles on the right side."""
        sparkle_positions = [
            (self.width - 80, 60),
            (self.width - 120, 90),
            (self.width - 50, 150),
        ]
        
        for sx, sy in sparkle_positions:
            self._draw_sparkle(draw, sx, sy, 6)
            
    def _draw_sparkle(self, draw: ImageDraw.ImageDraw, x: int, y: int, size: int) -> None:
        color = hex_to_rgb(self.theme['secondary']) # White sparkles
        draw.line([(x - size, y), (x + size, y)], fill=(*color, 180), width=2)
        draw.line([(x, y - size), (x, y + size)], fill=(*color, 180), width=2)


# ==================== MAIN GENERATION FUNCTION ====================
async def generate_welcome_card(
    user_pic_bytes: Optional[bytes] = None,
    user_name: str = "User",
    subtitle: str = "W E L C O M E   V I P",
    theme: str = 'gold',
    bg_path: Optional[str] = None
) -> io.BytesIO:
    """
    Generate a SUPER PREMIUM anime-style welcome card.
    """
    try:
        generator = WelcomeCardGenerator(bg_path=bg_path, theme=theme)
        
        # 1. Load Background
        bg = generator.load_background()
        
        # 2. Add Left-Side-Only Shadow Overlay (keeps right side bright)
        left_shadow = ImageProcessor.create_left_shadow_overlay((generator.width, generator.height), fade_distance=450)
        bg = Image.alpha_composite(bg, left_shadow)
        
        draw = ImageDraw.Draw(bg)
        
        # 3. Draw subtle decorations (Sparkles)
        generator.draw_decorations(draw)
        
        # --- LAYOUT SETTINGS ---
        pfp_size = DEFAULT_PFP_SIZE
        # Set exact coordinates for left side
        pfp_x = 70
        pfp_y = 70
        center_x = pfp_x + (pfp_size // 2)
        
        # 4. Process Profile Picture & Border
        if user_pic_bytes:
            try:
                pfp = Image.open(io.BytesIO(user_pic_bytes)).convert("RGBA")
                pfp = ImageOps.fit(pfp, (pfp_size, pfp_size), centering=(0.5, 0.5))
                
                mask = generator.create_pfp_mask(pfp_size)
                generator.draw_premium_border(draw, pfp_x, pfp_y, pfp_size)
                
                bg.paste(pfp, (pfp_x, pfp_y), mask)
            except Exception as e:
                logger.warning(f"Failed to process profile picture: {e}")
                _draw_default_avatar(draw, pfp_x, pfp_y, pfp_size, generator.theme)
        else:
            _draw_default_avatar(draw, pfp_x, pfp_y, pfp_size, generator.theme)
            
        # 5. Draw Text Information (DIRECTLY BELOW PFP)
        text_start_y = pfp_y + pfp_size + 25
        
        # Name with dimensions
        generator.draw_username(draw, user_name, center_x, text_start_y)
        
        # Subtitle below name
        generator.draw_subtitle(draw, subtitle, center_x, text_start_y + 45)
        
        # 6. Final Polish (Vignette)
        bg = ImageProcessor.add_vignette(bg, intensity=0.15)
        
        # 7. Convert and Return
        output = io.BytesIO()
        bg.convert("RGB").save(output, format="JPEG", quality=100, optimize=True)
        output.seek(0)
        
        return output
        
    except Exception as e:
        logger.error(f"Error generating welcome card: {e}")
        raise


def _draw_default_avatar(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    size: int,
    theme: dict
) -> None:
    """Draw default premium avatar placeholder when no profile picture is visible."""
    primary = theme['primary']
    
    # Dark circle with Gold outline
    draw.ellipse(
        (x, y, x + size, y + size),
        fill="#2C2F33",
        outline=primary,
        width=6
    )
    
    center_x = x + size // 2
    center_y = y + size // 2
    
    # Simple abstract silhouette  
    head_radius = size // 5
    draw.ellipse(
        (center_x - head_radius, center_y - head_radius - size//8,
         center_x + head_radius, center_y + head_radius - size//8),
        fill="#7289DA"
    )
    
    body_width = size // 2.5
    draw.ellipse(
        (center_x - body_width, center_y + size//10,
         center_x + body_width, center_y + size//2 + size//6),
        fill="#7289DA"
    )


# ==================== CONVENIENCE FUNCTIONS ====================
async def generate_welcome_card_from_url(
    pic_url: Optional[str],
    user_name: str,
    **kwargs
) -> io.BytesIO:
    """Fetch image from URL and generate card."""
    import aiohttp
    
    if not pic_url:
        return await generate_welcome_card(None, user_name, **kwargs)
        
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(pic_url) as response:
                if response.status == 200:
                    pic_bytes = await response.read()
                    return await generate_welcome_card(pic_bytes, user_name, **kwargs)
    except Exception as e:
        logger.warning(f"Failed to fetch image from URL: {e}")
    
    return await generate_welcome_card(None, user_name, **kwargs)

# ==================== EXPORTS ====================
__all__ = [
    'generate_welcome_card',
    'generate_welcome_card_from_url',
    'WelcomeCardGenerator',
    'FontLoader',
    'ImageProcessor'
]