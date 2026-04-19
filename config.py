"""Central configuration for Moses' Staff game."""
from pathlib import Path

# --- timing ---------------------------------------------------------------
DURATION_PRESETS = {"easy": 90, "default": 180, "hard": 300}
DEFAULT_DURATION = "default"
WARMUP_SECONDS = 3

# --- battle dynamics ------------------------------------------------------
# Fraction of battlefield pushed per second. Tuned so that with the default
# 3-minute round, holding arms up ~100% of the time *barely* wins at the end,
# and dropping for more than ~40% of the round loses. Makes the round feel
# like a sustained physical challenge instead of a 10-second sprint.
PUSH_RATE = 0.003
# Amalek surges 3x faster when Moses's hands drop than Israel advances when
# they're up. Biblically loaded — every rest hurts more than it helps — and
# mathematically forces >75% arms-up time to win a 3-minute round, which
# demands either serious stamina or helpers (Aaron and Hur).
PUSH_RATE_DOWN_MULT = 3.0
# Hysteresis band in normalized frame-Y units; wrist must clear shoulder by
# this much to flip the arms-up flag. Prevents flicker.
HYSTERESIS = 0.03

# --- display --------------------------------------------------------------
WINDOW_W = 1600
WINDOW_H = 900
BATTLEFIELD_H_FRAC = 0.55  # top portion; remainder is webcam + HUD
FPS = 30
# Sized so every sprite (base + 10 variants = 11) shows up at least once per
# army; any extra beyond 11 recycles the pool.
SOLDIERS_PER_SIDE = 11
SOLDIER_STEP_PX = 70  # horizontal spacing between soldiers in a column
SOLDIER_VARIANT_COUNT = 10  # how many variants per side to generate via edit

# --- paths ----------------------------------------------------------------
ROOT = Path(__file__).parent
ASSETS_DIR = ROOT / "assets"
AUDIO_DIR = ROOT / "audio"

# --- audio ----------------------------------------------------------------
# Generated via Gemini Lyria Realtime (streams 48kHz 16-bit stereo PCM).
LYRIA_MODEL_ID = "models/lyria-realtime-exp"
MUSIC_DURATION_S = 45  # how many seconds of loopable music to capture
MUSIC_VOLUME = 0.45  # pygame.mixer volume 0..1
AMBIENCE_DURATION_S = 35
AMBIENCE_VOLUME = 0.35  # under the music so it's texture, not dominant

# Weighted text prompts fed to Lyria for the battle music. Multiple prompts
# with weights shape the mood more reliably than a single long sentence.
BATTLE_MUSIC_PROMPTS = [
    ("cinematic orchestral desert battle march", 1.0),
    ("middle eastern percussion, frame drums, tambourine", 0.7),
    ("heroic triumphant brass section", 0.8),
    ("driving strings, rhythmic, 110 BPM", 0.6),
    ("playful cartoon adventure score, tower defense game style", 0.5),
]

# Ambience = battle SFX texture. Lyria is a music model, so these prompts
# lean on percussion, chants, and "heavy metal clashing" kinds of language.
BATTLE_AMBIENCE_PROMPTS = [
    ("battlefield ambience with metal swords clashing rhythmically", 1.0),
    ("distant soldiers shouting war cries, call-and-response chant", 0.9),
    ("war drums pounding, low frame drums, stomping feet", 0.85),
    ("gritty percussion, anvil hits, shield bashes", 0.7),
    ("no melody, no vocals singing pitched notes, just rhythmic percussion and shouting", 0.6),
]

# --- gemini ---------------------------------------------------------------
# Gemini image generation model. Nano Banana Pro (gemini-3-pro-image-preview)
# handles text rendering dramatically better than 2.5 Flash — worth it for the
# victory banners.
MODEL_ID = "gemini-3-pro-image-preview"

STYLE_PREFIX = (
    "Cartoon game sprite in the style of Kingdom Rush (the Ironhide mobile "
    "tower-defense game). Chunky cartoon proportions (slightly oversized "
    "head, stocky body), bold dark outlines, saturated hand-painted palette, "
    "flat shading with clean painted highlights. Polished, expressive, "
    "cheerful tone. Single subject centered in the frame, no text, no "
    "watermark, no UI elements. "
    "PNG with a fully transparent background — alpha channel only, with "
    "no sky, no ground, no drop shadow, and no solid fill around the subject. "
)

ART_PROMPTS = {
    "background.png": (
        "Wide desert battlefield at Rephidim in the style of Kingdom Rush "
        "tower-defense game backdrops. Cartoon illustration, bold outlines, "
        "saturated hand-painted palette. Red-brown stylized mesas on the "
        "horizon, warm sandy ground with a few tufts of scrub grass and a "
        "scattered stones, pale turquoise sky with stylized fluffy clouds. "
        "Empty center — no characters, no soldiers. "
        "Wide horizontal 16:9 composition, the whole image is the scene "
        "(fully opaque, NOT transparent)."
    ),
    "israelite.png": (
        STYLE_PREFIX
        + "A single Israelite foot soldier from the Exodus era, facing right. "
        "Tan linen tunic with a blue sash at the waist, leather sandals, "
        "bronze round shield strapped to the left arm, bronze-tipped wooden "
        "spear held upright in the right hand. Short brown beard, dark "
        "curly hair, determined and hopeful expression. Full body, standing "
        "heroic pose."
    ),
    "amalekite.png": (
        STYLE_PREFIX
        + "A single Amalekite warrior from the Exodus era, facing left. "
        "Dark tunic with red trim, leather wraps on the forearms and shins, "
        "curved bronze scimitar raised in the right hand, small round "
        "studded leather shield in the left hand. Long black hair, black "
        "beard, fierce cartoon snarl. Full body, aggressive standing pose."
    ),
    "moses_icon.png": (
        STYLE_PREFIX
        + "Cartoon Moses — long white beard, flowing tan robe with a red "
        "sash, simple sandals — standing with both arms raised high "
        "overhead, holding a knotted wooden staff above his head. Iconic "
        "heroic silhouette, centered composition, no hilltop, no rays, "
        "no scenery behind him."
    ),
    # NOTE: victory banners skip the STYLE_PREFIX transparency directive —
    # it caused Nano Banana Pro to paint a literal gray-and-white checkerboard
    # INTO the image (its "transparent indicator"). Instead we ask for a plain
    # solid white background; the chroma-key in art_gen strips it cleanly.
    "victory_israel.png": (
        "A decorative cartoon ribbon banner with the hand-lettered text "
        "'ISRAEL PREVAILS' in bold serif capitals across the center. "
        "Cartoon game art style reminiscent of Kingdom Rush: thick dark "
        "outlines, saturated gold-and-deep-blue palette, olive branches "
        "flanking the ribbon. The banner is centered on a LARGE PLAIN "
        "SOLID WHITE BACKGROUND — pure #FFFFFF flat white filling the "
        "entire frame around the banner. NOT a transparency checkerboard, "
        "NOT a grid pattern, NOT gradients — just flat uniform white. "
        "No sky, no scene, no shadow."
    ),
    "victory_amalek.png": (
        "A decorative cartoon parchment scroll with the hand-lettered text "
        "'AMALEK PREVAILS' in bold serif capitals across the center. "
        "Cartoon game art style reminiscent of Kingdom Rush: thick dark "
        "outlines, aged parchment and bronze palette, a pair of crossed "
        "curved scimitars beneath the scroll. The scroll is centered on a "
        "LARGE PLAIN SOLID WHITE BACKGROUND — pure #FFFFFF flat white "
        "filling the entire frame. NOT a transparency checkerboard, NOT "
        "a grid pattern, NOT gradients — just flat uniform white. "
        "No sky, no scene, no shadow."
    ),
}

# Variation prompts used with image-edit (reference image + prompt).
# Previous pass held the pose constant and only swapped gear — the army ended
# up looking like ten clones with different weapons. These prompts explicitly
# vary POSE and PERSONALITY (charging, kneeling, cheering, stalking, leaping)
# while locking the art style and overall character scale.
ISRAELITE_VARIATION_PROMPTS = [
    "The soldier is charging forward dramatically, body leaning into the attack, spear thrust out ahead, mouth open in a battle cry, shield raised forward. Determined, fearsome expression. Facing right.",
    "The soldier is kneeling on one knee in prayer, head bowed, spear planted upright beside him, shield resting on the ground. Peaceful, reverent expression. Facing right.",
    "The soldier is raising his spear and free arm high overhead in an exuberant rally-cheer, head tilted back, mouth wide open shouting. Joyful, triumphant. Facing right.",
    "The soldier is crouched low behind his round shield in a tight defensive stance, only the upper half of his face visible over the shield rim, spear braced low and forward. Wary, watchful. Facing right.",
    "A young soldier sprinting forward mid-stride, carrying a long cloth banner pole instead of the spear, banner streaming behind him. Eager, hopeful, mouth open in a rallying shout. Facing right.",
    "An older commander standing tall and proud, one hand on hip, the other arm extended pointing decisively forward as if commanding the advance. Streaks of gray in the beard, calm confident expression. Facing right.",
    "The soldier is limping forward wearily, leaning heavily on his spear like a walking staff, shield drooping at his side. Exhausted but resolute, jaw set. Facing right.",
    "The soldier is blowing a ram's horn shofar held up to the sky, cheeks puffed out, eyes squeezed shut, his spear held diagonally across his body in the other hand. Facing right.",
    "The soldier is striding forward mid-step with swagger, one foot lifted, spear casually slung over his shoulder, a small fearless smile. Cheerful, cocky. Facing right.",
    "The soldier is planted in a heavy wide stance braced to receive a charge, both hands gripping his spear horizontally across his chest, brows furrowed. Grim, immovable. Facing right.",
]
AMALEKITE_VARIATION_PROMPTS = [
    "The warrior is mid-swing with his curved scimitar slashing across his body in a wide arc, weight shifted dramatically onto one leg, snarling wide-mouthed battle cry. Facing left.",
    "The warrior is crouched low in a stalking prowl, scimitar held low and back ready to strike, body coiled like a predator, vicious grin. Facing left.",
    "The warrior is leaping into the air with both feet off the ground, scimitar raised high overhead for a downward strike, roaring with mouth wide open. Facing left.",
    "The warrior is standing with arms spread wide, head thrown back, roaring defiance at the sky, scimitar dangling loose in one hand. Bold, theatrical. Facing left.",
    "The warrior is drawing a composite bow back to full tension, one eye closed in aim, body angled in a classic archer stance. Replace the scimitar with a bow; add a quiver on his back. Facing left.",
    "The warrior is taunting — beating his bare chest with his free fist, his scimitar planted point-down in the ground before him, chin jutted out, sneering. Facing left.",
    "The warrior is charging mid-stride with a long spear leveled at chest height like a cavalry lance, teeth gritted in concentration. Replace the scimitar with the long spear. Facing left.",
    "The warrior is spinning mid-twirl with a scimitar in each hand slashing out in opposite directions, hair and tunic flaring out dramatically. Give him a second scimitar. Facing left.",
    "The warrior is kneeling heavily on one knee, scimitar planted point-down in the dirt as a support, one arm resting on the raised knee, glaring forward with battle-weary intensity. Facing left.",
    "The warrior is standing atop a small rock with his scimitar raised triumphantly skyward, one foot planted on the rock, shouting victoriously. Facing left.",
]

# --- colors (RGB) ---------------------------------------------------------
COLOR_BG = (20, 18, 24)
COLOR_ISRAEL = (90, 150, 220)
COLOR_AMALEK = (200, 80, 70)
COLOR_ARMS_UP = (120, 220, 140)
COLOR_ARMS_DOWN = (220, 90, 90)
COLOR_TEXT = (240, 235, 220)
COLOR_HUD_BG = (35, 32, 40)
