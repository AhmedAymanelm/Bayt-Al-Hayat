import os
import json
import asyncio
import httpx
import shutil
import cloudinary
import cloudinary.uploader
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv
from app.utils.settings_helper import get_env_or_db
from app.database import async_session_maker

load_dotenv(override=True)

class AIVideoService:
    OUTPUT_DIR = Path("videos")

    # ── Neuroscience Pattern → Symbol Mapping ────────────────────────────────
    NEURO_SYMBOL_MAP = {
        "Fight":  "was_scepter",   
        "Flight": "scarab",        
        "Freeze": "djed",          
        "Fawn":   "isis_knot",     
        "Mixed":  "ankh",          
    }

    COMPREHENSIVE_SYMBOLS = {
        "wise":    "lotus",         
        "insight": "eye_of_horus",  
        "default": "ankh",          
    }

    # ── Symbol definitions (3 scenes each) ────────────────────────────────────
    SYMBOLS = {
        "ankh": {
            "name_ar": "مفتاح الحياة (عنخ)",
            "prompt_image": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1774325883/egyptian_symbols/kah1qprn6qgrzyrhgkxd.jpg",
            "video_prompts": [
                "Extreme cinematic wide shot. An infinite {bg_color} void stretches endlessly. From the absolute center, a single microscopic point of pure {accent_color} light ignites, then EXPLODES outward in a breathtaking slow-motion energy burst. Thousands of luminous particles spiral outward like a cosmic supernova, each trailing ribbons of {accent_color} fire. Volumetric god-rays pierce through swirling nebula clouds. Camera slowly pushes forward through the spectacle with hyper-realistic depth of field. Ultra photorealistic, IMAX quality. {vibe_desc}.",
                "Sweeping cinematic orbital reveal. An ENORMOUS ancient Egyptian Ankh materializes from pure radiant energy — its surface living obsidian wrapped in pulsing {accent_color} plasma. Divine rings of light expand rhythmically across a {bg_color} cosmic ocean. Tens of thousands of glittering particles orbit the symbol like a galaxy forming. Sacred geometric patterns bloom around it. Golden lens flares cut dramatically across the frame. Deep cinematic bokeh, photorealistic, deeply emotional. {vibe_desc}.",
                "Epic cinematic finale. The Ankh EXPLODES into a massive, reality-bending supernova of pure {accent_color} liquid light. The camera flies forward INTO the center of the explosion, passing through vibrant nebula clouds that form the user's zodiac constellation in the stars. The world is reborn in blinding brightness. Epic, triumphant, deep bass energy. {vibe_desc}."
            ]
        },
        "djed": {
            "name_ar": "عمود جد",
            "prompt_image": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1774325013/egyptian_symbols/q7szwspoudjnxsnxiekr.jpg",
            "video_prompts": [
                "Cinematic low-angle ground-level shot. The {bg_color} earth trembles with deep resonant power. Enormous fissures crack open in slow motion, releasing blinding shafts of {accent_color} energy erupting upward like geysers of pure light. Clouds of crystalline dust catch and scatter the divine rays. Camera slowly cranes upward through the chaos. Photorealistic, IMAX scale, deeply grounding. {vibe_desc}.",
                "Epic cinematic reveal. The earth parts to birth a colossal ancient Egyptian Djed pillar rising majestically. Its surface is ancient carved stone interlacd with channels of living {accent_color} energy flowing upward. Each horizontal band ignites sequentially sending shockwaves of light radiating outward. Volumetric fog swirls dramatically at the base. Camera circles slowly in reverent orbit. Sacred, powerful. {vibe_desc}.",
                "Epic cinematic finale. The Djed Pillar reaches out with immense white-hot {accent_color} lightning, anchoring the entire universe. A massive circular shockwave ripples through the {bg_color} cosmos, turning every star into a glowing Egyptian hieroglyph of power. The camera orbits rapidly as the Djed becomes the central axis of a spinning galaxy. Supreme stability and god-like scale. {vibe_desc}."
            ]
        },
        "isis_knot": {
            "name_ar": "عقدة إيزيس",
            "prompt_image": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1774325362/egyptian_symbols/bqxlwovjitmq8mwsgubs.jpg",
            "video_prompts": [
                "Ethereal cinematic dolly shot. From edge to edge of an infinite {bg_color} dreamscape, luminous {accent_color} silk ribbons materialize from the void — hundreds of them, flowing in slow motion like auroras given physical form. They weave through each other hypnotically, each touch creating sparks of warm light. Camera glides forward through the ribbons, fabric softly catching diffracted light. Deeply beautiful, otherworldly. {vibe_desc}.",
                "Breathtaking cinematic reveal. The ethereal ribbons converge and weave into a breathtaking ancient Egyptian Tyet Isis Knot — its form built of living light, warm {accent_color} and deep {bg_color} intertwined. A luminous halo pulses gently from its heart sending waves of protective energy outward. Intricate sacred geometric patterns bloom behind it like a divine mandala. Camera slowly pulls back to reveal its full cosmic scale. {vibe_desc}.",
                "Epic cinematic finale. The Isis Knot weaves its ribbons into a massive, translucent protective cocoon of {accent_color} light that wraps the entire earth. A million glowing butterflies made of pure energy erupt from its center, filling the {bg_color} sky like a divine migration. The camera follows them toward a blinding, hopeful sunrise at the edge of the universe. Healing power at cosmic scale. {vibe_desc}."
            ]
        },
        "was_scepter": {
            "name_ar": "صولجان الواس",
            "prompt_image": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1774325129/egyptian_symbols/tcblvoi4ydc0bnfdrahg.jpg",
            "video_prompts": [
                "Explosive cinematic power shot. In the heart of a {bg_color} void, a crack of {accent_color} lightning tears reality apart in slow motion — branching plasma fractals spread outward, each arc crackling with energy particles. The lightning implodes back to a single blinding point pulsing with contained power. Camera shakes subtly from the raw force. Ultra-detailed, hyper-real. {vibe_desc}.",
                "Majestic cinematic crane-up reveal. The ancient Egyptian Was Scepter ERUPTS upward — towering, burnished {accent_color} metal carved with glowing hieroglyphs. Living electricity coils up its length from the forked base to the divine animal head leaving trails of plasma. Camera cranes up its full impossible length from earth to sky against a {bg_color} cosmic backdrop. God-rays frame it like a divine monument. Awe-inspiring. {vibe_desc}.",
                "Epic cinematic finale. The Was Scepter strikes the invisible floor of space, sending a cataclysmic shockwave of {accent_color} energy that shatters reality itself into floating geometric glass shards. Behind the shattered reality, a glorious new {bg_color} universe is revealed, pulsing with ultimate authority and limitless potential. Camera rushes forward into the new dimension. God-like power. {vibe_desc}."
            ]
        },
        "scarab": {
            "name_ar": "الجعران",
            "prompt_image": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1774325432/egyptian_symbols/lbedn0572f6rxhb7jf5d.jpg",
            "video_prompts": [
                "Cinematic macro-to-wide tracking shot. An ocean of {bg_color} cosmic sand swirls in spectacular slow motion — each grain catches {accent_color} light like a miniature star. The swirling accelerates into a perfect spiral storm converging on a single glowing point. Camera moves through the spiraling storm impossibly close to the spinning grains before pulling wide to reveal its colossal galactic scale. {vibe_desc}.",
                "Breathtaking cinematic emergence. The sand storm PARTS dramatically — an ancient Egyptian Scarab of extraordinary scale rises within. Its iridescent {accent_color} surface shifts between colors. As its magnificent wings unfurl they fill the entire frame — each membrane reveals sacred geometric light patterns and luminous star maps. The cosmic sand rains upward defying gravity. Camera orbits in slow reverence. {vibe_desc}.",
                "Epic cinematic finale. The colossal Scarab beats its wings, tearing open a glowing {accent_color} wormhole in the fabric of space-time. It dives headfirst into the portal, dragging the camera along at hyper-speed through a tunnel of swirling stardust and sacred geometry. We emerge into a blindingly beautiful {bg_color} utopia full of floating golden pyramids. Breathtaking interstellar rebirth. {vibe_desc}."
            ]
        },
        "eye_of_horus": {
            "name_ar": "عين حورس",
            "prompt_image": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1774325968/egyptian_symbols/hircpygiu1px1hhzul92.jpg",
            "video_prompts": [
                "Ultra-cinematic deep space push shot. An infinite {bg_color} starfield stretches in all directions. Camera begins a slow hypnotic pull-forward through the cosmos. Threads of {accent_color} celestial energy between distant stars become visible forming a vast invisible web. In the web's center, light begins to concentrate and twist into a spiral of cosmic dust. Anticipation builds with each frame. IMAX scale, ultra-detailed, majestic silence. {vibe_desc}.",
                "Legendary cinematic reveal. The cosmic spiral resolves into an ancient Egyptian Eye of Horus of divine proportions suspended in deep space. Every line and curve composed of concentrated starlight and {accent_color} plasma. The pupil opens slowly revealing infinite depth within. BEAMS of focused {accent_color} light shoot outward across the cosmos. Waves of protective geometric light radiate outward. Camera holds in reverent close-up before pulling back to reveal its universal scale. {vibe_desc}.",
                "Epic cinematic finale. The Eye of Horus suddenly shoots a colossal, blinding beam of {accent_color} laser-light directly at the camera, engulfing the viewer in pure, transcendent energy. As the light fades, the viewer is flying at warp speed through a magnificent {bg_color} galaxy shaped exactly like the Eye. Ultimate enlightenment and cosmic awakening. {vibe_desc}."
            ]
        },
        "lotus": {
            "name_ar": "زهرة اللوتس",
            "prompt_image": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1774325681/egyptian_symbols/aduqhwyyb792zwwq0rap.jpg",
            "video_prompts": [
                "Breathtaking underwater-to-surface cinematic shot. An infinite body of luminous {bg_color} water stretches in all directions — surface perfectly still and mirror-like reflecting the cosmos. Beneath the surface, slow-motion {accent_color} light pulses rise from infinite depths like heartbeats. Camera begins below the surface looking up at the shimmering boundary between water and sky. Individual droplets of light detach and float upward in perfect slow motion. Ethereal, healing. {vibe_desc}.",
                "Magical cinematic reveal from below. Concentrated light erupts upward through the surface in a spectacular slow-motion crown splash of pure {accent_color} energy. A sacred ancient Egyptian Lotus flower blooms in real-time — each petal unfolding in divine slow motion, revealing bioluminescent patterns and sacred geometry within. Each petal edge radiates soft prismatic light. Camera slowly circles as the bloom reaches its full divine glory. {vibe_desc}.",
                "Epic cinematic finale. The Lotus flower transcends, rapidly expanding until its glowing {accent_color} petals eclipse the entire sky. It detonates in a harmonious big bang of light, transforming the {bg_color} ocean into a brilliant galaxy of floating stars. The camera ascends at light-speed through the core of the galaxy, leaving a trail of pure creation. Cosmic climax. {vibe_desc}."
            ]
        }
    }

    # ── Zodiac Sign → Color Mapping ───────────────────────────────────────────
    ZODIAC_COLORS = {
        "الحمل":    {"bg": "deep crimson and dark red",         "accent": "fiery gold",           "vibe": "Fierce, energetic, bold and powerful atmosphere."},
        "الثور":    {"bg": "deep emerald green and dark earth",  "accent": "warm golden brown",    "vibe": "Grounded, rich, deeply sensual and stable atmosphere."},
        "الجوزاء":  {"bg": "deep golden yellow and dark silver", "accent": "shimmering silver",    "vibe": "Curious, intellectual, playful and lively atmosphere."},
        "السرطان":  {"bg": "deep moonlit silver and dark ocean", "accent": "soft pearl white",     "vibe": "Nurturing, emotional, gentle and intuitive atmosphere."},
        "الأسد":    {"bg": "deep burnt orange and dark amber",   "accent": "radiant warm gold",    "vibe": "Majestic, confident, warm and radiant atmosphere."},
        "العذراء":  {"bg": "deep olive green and dark beige",    "accent": "soft quiet gold",      "vibe": "Precise, calm, pure and quietly elegant atmosphere."},
        "الميزان":  {"bg": "deep rose and dark teal",            "accent": "delicate rose gold",   "vibe": "Balanced, harmonious, elegant and refined atmosphere."},
        "العقرب":   {"bg": "deep burgundy and dark purple",      "accent": "intense violet",       "vibe": "Transformative, mysterious, powerful and magnetic atmosphere."},
        "القوس":    {"bg": "deep indigo and dark violet",        "accent": "bright turquoise",     "vibe": "Adventurous, optimistic, expansive and philosophical atmosphere."},
        "الجدي":    {"bg": "deep slate gray and dark charcoal",  "accent": "heritage gold",        "vibe": "Disciplined, ambitious, steady and enduring atmosphere."},
        "الدلو":    {"bg": "deep electric blue and dark cosmic", "accent": "electric turquoise",   "vibe": "Innovative, futuristic, free-spirited and visionary atmosphere."},
        "الحوت":    {"bg": "deep aqua-blue and dark sea green",  "accent": "poetic soft violet",   "vibe": "Dreamy, spiritual, compassionate and transcendent atmosphere."},
        # English fallback
        "Aries":       {"bg": "deep crimson and dark red",         "accent": "fiery gold",           "vibe": "Fierce, energetic, bold and powerful atmosphere."},
        "Taurus":      {"bg": "deep emerald green and dark earth",  "accent": "warm golden brown",    "vibe": "Grounded, rich, deeply sensual and stable atmosphere."},
        "Gemini":      {"bg": "deep golden yellow and dark silver", "accent": "shimmering silver",    "vibe": "Curious, intellectual, playful and lively atmosphere."},
        "Cancer":      {"bg": "deep moonlit silver and dark ocean", "accent": "soft pearl white",     "vibe": "Nurturing, emotional, gentle and intuitive atmosphere."},
        "Leo":         {"bg": "deep burnt orange and dark amber",   "accent": "radiant warm gold",    "vibe": "Majestic, confident, warm and radiant atmosphere."},
        "Virgo":       {"bg": "deep olive green and dark beige",    "accent": "soft quiet gold",      "vibe": "Precise, calm, pure and quietly elegant atmosphere."},
        "Libra":       {"bg": "deep rose and dark teal",            "accent": "delicate rose gold",   "vibe": "Balanced, harmonious, elegant and refined atmosphere."},
        "Scorpio":     {"bg": "deep burgundy and dark purple",      "accent": "intense violet",       "vibe": "Transformative, mysterious, powerful and magnetic atmosphere."},
        "Sagittarius": {"bg": "deep indigo and dark violet",        "accent": "bright turquoise",     "vibe": "Adventurous, optimistic, expansive and philosophical atmosphere."},
        "Capricorn":   {"bg": "deep slate gray and dark charcoal",  "accent": "heritage gold",        "vibe": "Disciplined, ambitious, steady and enduring atmosphere."},
        "Aquarius":    {"bg": "deep electric blue and dark cosmic", "accent": "electric turquoise",   "vibe": "Innovative, futuristic, free-spirited and visionary atmosphere."},
        "Pisces":      {"bg": "deep aqua-blue and dark sea green",  "accent": "poetic soft violet",   "vibe": "Dreamy, spiritual, compassionate and transcendent atmosphere."},
    }

    DEFAULT_COLORS = {
        "bg": "deep dark cosmic blue and starry black",
        "accent": "shimmering soft gold",
        "vibe": "Calm, mystical, deeply introspective atmosphere."
    }

    # ── Zodiac Sign → Cinematic Scene 1 (symbol materializes from void) ────────
    ZODIAC_SCENE1_PROMPTS = {
        # Arabic
        "الحمل":    "Breathtaking IMAX cinematic shot. In a profound {bg_color} cosmic void, hyper-realistic glowing {accent_color} nebula clouds swirl and compress, slowly birthing the majestic, ethereal spirit of a Ram. Glowing stardust flows through its horns. No artificial lines, pure celestial particle physics. {vibe_desc}.",
        "الثور":    "Breathtaking IMAX cinematic shot. From a rich, deep {bg_color} galaxy, massive waves of warm {accent_color} cosmic stardust gather in slow motion, forming the magnificent, grounded silhouette of a colossal Taurus Bull made entirely of living light. No drawn lines. {vibe_desc}.",
        "الجوزاء":  "Breathtaking IMAX cinematic shot. Within an infinite {bg_color} universe, two brilliant streams of {accent_color} plasma dance around each other in an elegant double helix, resolving into the ethereal silhouettes of the celestial Twins. Ultra photorealistic, glowing aura. {vibe_desc}.",
        "السرطان":  "Breathtaking IMAX cinematic shot. From a deep {bg_color} holographic cosmic ocean, a gigantic glorious silver moon rises. Ethereal {accent_color} nebula gases drift across its surface, naturally forming the majestic, living silhouette of a celestial Crab. Highly cinematic, no artificial lines. {vibe_desc}.",
        "الأسد":    "Breathtaking IMAX cinematic shot. A supernova explodes in a {bg_color} abyss, radiating blinding {accent_color} volumetric light that shapes into the fierce, roaring spirit of a majestic cosmic Lion. Pure living fire and stardust, hyper-realistic depth of field. {vibe_desc}.",
        "العذراء":  "Breathtaking IMAX cinematic shot. Delicate, shimmering {accent_color} auroras weave together across a serene {bg_color} starfield, slowly forming the graceful, angelic silhouette of the Virgo Maiden. Ethereal, hyper-detailed particle simulation. {vibe_desc}.",
        "الميزان":  "Breathtaking IMAX cinematic shot. Perfect harmony in a {bg_color} cosmos as sweeping arcs of {accent_color} celestial light descend, perfectly balancing to form an awe-inspiring, glowing scale of justice made of pure stardust. Symmetrical, divine, photorealistic. {vibe_desc}.",
        "العقرب":   "Breathtaking IMAX cinematic shot. From a mysterious, magnetic {bg_color} dark matter cloud, intense {accent_color} energy pulses shape the towering, fierce silhouette of a cosmic Scorpion. Its tail curves with dangerous glowing plasma. Ultra-cinematic, deep shadow. {vibe_desc}.",
        "القوس":    "Breathtaking IMAX cinematic shot. A blinding {accent_color} shooting star tears through a {bg_color} galaxy, its luminous trail dynamically swirling into the majestic form of a celestial Archer pulling a bow of pure light. Epic momentum, star-birth physics. {vibe_desc}.",
        "الجدي":    "Breathtaking IMAX cinematic shot. Massive, ancient {accent_color} crystalline light erupts from a cosmic {bg_color} mountain range, sculpting the mighty Sea-Goat out of living diamond stardust. Unshakable, enduring power, hyper-realistic cosmic scales. {vibe_desc}.",
        "الدلو":    "Breathtaking IMAX cinematic shot. Advanced, glowing {accent_color} quantum liquid pours continuously across a {bg_color} infinite galaxy, forming the vast silhouette of the Water-Bearer. The liquid light transforms into a billion new stars. Highly futuristic. {vibe_desc}.",
        "الحوت":    "Breathtaking IMAX cinematic shot. In a tranquil {bg_color} cosmic ocean, two magnificent ethereal fishes made of flowing, luminescent {accent_color} stardust swim in an eternal circle. Trailing auroras of light follow them. Profoundly peaceful, photorealistic. {vibe_desc}.",
        
        # English fallback
        "Aries":       "Breathtaking IMAX cinematic shot. In a profound {bg_color} cosmic void, hyper-realistic glowing {accent_color} nebula clouds swirl and compress, slowly birthing the majestic, ethereal spirit of a Ram. Glowing stardust flows through its horns. No artificial lines, pure celestial particle physics. {vibe_desc}.",
        "Taurus":      "Breathtaking IMAX cinematic shot. From a rich, deep {bg_color} galaxy, massive waves of warm {accent_color} cosmic stardust gather in slow motion, forming the magnificent, grounded silhouette of a colossal Taurus Bull made entirely of living light. No drawn lines. {vibe_desc}.",
        "Gemini":      "Breathtaking IMAX cinematic shot. Within an infinite {bg_color} universe, two brilliant streams of {accent_color} plasma dance around each other in an elegant double helix, resolving into the ethereal silhouettes of the celestial Twins. Ultra photorealistic, glowing aura. {vibe_desc}.",
        "Cancer":      "Breathtaking IMAX cinematic shot. From a deep {bg_color} holographic cosmic ocean, a gigantic glorious silver moon rises. Ethereal {accent_color} nebula gases drift across its surface, naturally forming the majestic, living silhouette of a celestial Crab. Highly cinematic, no artificial lines. {vibe_desc}.",
        "Leo":         "Breathtaking IMAX cinematic shot. A supernova explodes in a {bg_color} abyss, radiating blinding {accent_color} volumetric light that shapes into the fierce, roaring spirit of a majestic cosmic Lion. Pure living fire and stardust, hyper-realistic depth of field. {vibe_desc}.",
        "Virgo":       "Breathtaking IMAX cinematic shot. Delicate, shimmering {accent_color} auroras weave together across a serene {bg_color} starfield, slowly forming the graceful, angelic silhouette of the Virgo Maiden. Ethereal, hyper-detailed particle simulation. {vibe_desc}.",
        "Libra":       "Breathtaking IMAX cinematic shot. Perfect harmony in a {bg_color} cosmos as sweeping arcs of {accent_color} celestial light descend, perfectly balancing to form an awe-inspiring, glowing scale of justice made of pure stardust. Symmetrical, divine, photorealistic. {vibe_desc}.",
        "Scorpio":     "Breathtaking IMAX cinematic shot. From a mysterious, magnetic {bg_color} dark matter cloud, intense {accent_color} energy pulses shape the towering, fierce silhouette of a cosmic Scorpion. Its tail curves with dangerous glowing plasma. Ultra-cinematic, deep shadow. {vibe_desc}.",
        "Sagittarius": "Breathtaking IMAX cinematic shot. A blinding {accent_color} shooting star tears through a {bg_color} galaxy, its luminous trail dynamically swirling into the majestic form of a celestial Archer pulling a bow of pure light. Epic momentum, star-birth physics. {vibe_desc}.",
        "Capricorn":   "Breathtaking IMAX cinematic shot. Massive, ancient {accent_color} crystalline light erupts from a cosmic {bg_color} mountain range, sculpting the mighty Sea-Goat out of living diamond stardust. Unshakable, enduring power, hyper-realistic cosmic scales. {vibe_desc}.",
        "Aquarius":    "Breathtaking IMAX cinematic shot. Advanced, glowing {accent_color} quantum liquid pours continuously across a {bg_color} infinite galaxy, forming the vast silhouette of the Water-Bearer. The liquid light transforms into a billion new stars. Highly futuristic. {vibe_desc}.",
        "Pisces":      "Breathtaking IMAX cinematic shot. In a tranquil {bg_color} cosmic ocean, two magnificent ethereal fishes made of flowing, luminescent {accent_color} stardust swim in an eternal circle. Trailing auroras of light follow them. Profoundly peaceful, photorealistic. {vibe_desc}.",
    }
    
    # ── You can paste direct image URLs (Cloudinary, Imgur) here to force Runway to animate them (Image-to-Video) ──
    ZODIAC_IMAGES_REF = {
        "الحمل": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1774843836/zodiac_images_refs/krr9oddbpcatnlelruaw.png", 
        "الثور": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1775843556/zodiac_signs/crg9g8o2chbfdg2vzoo6.png", 
        "الجوزاء": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1774843947/zodiac_images_refs/wxuhxox4tynbd6mida8m.png", 
        "السرطان": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1774843749/zodiac_images_refs/gxzz5wtcu47qhe3svxbg.png", 
        "الأسد": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1775843400/zodiac_signs/j1udnopsrwhp2qae3hpc.png", 
        "العذراء": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1774844268/zodiac_images_refs/phwba61lrthkgnjt0znc.png", 
        "الميزان": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1774844314/zodiac_images_refs/rrw2duyspxjkpqhk67p4.png", 
        "العقرب": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1775843228/zodiac_signs/xhrqzgdmu9hywlfpjlpy.png", 
        "القوس": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1774844420/zodiac_images_refs/rbmzrxxtkpxazpdykwlc.png", 
        "الجدي": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1775843139/zodiac_signs/gupnhdbo8wa1sqzqghf4.png", 
        "الدلو": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1774844541/zodiac_images_refs/uuvb8ewex6dlw6jfrnqb.png", 
        "الحوت": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1774844579/zodiac_images_refs/p2emtfj9e6ibbyzok09r.png",
        "Aries": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1774843836/zodiac_images_refs/krr9oddbpcatnlelruaw.png", 
        "Taurus": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1775843556/zodiac_signs/crg9g8o2chbfdg2vzoo6.png", 
        "Gemini": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1774843947/zodiac_images_refs/wxuhxox4tynbd6mida8m.png", 
        "Cancer": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1774843749/zodiac_images_refs/gxzz5wtcu47qhe3svxbg.png", 
        "Leo": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1775843400/zodiac_signs/j1udnopsrwhp2qae3hpc.png", 
        "Virgo": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1774844268/zodiac_images_refs/phwba61lrthkgnjt0znc.png", 
        "Libra": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1774844314/zodiac_images_refs/rrw2duyspxjkpqhk67p4.png", 
        "Scorpio": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1775843228/zodiac_signs/xhrqzgdmu9hywlfpjlpy.png", 
        "Sagittarius": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1774844420/zodiac_images_refs/rbmzrxxtkpxazpdykwlc.png", 
        "Capricorn": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1775843139/zodiac_signs/gupnhdbo8wa1sqzqghf4.png", 
        "Aquarius": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1774844541/zodiac_images_refs/uuvb8ewex6dlw6jfrnqb.png", 
        "Pisces": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1774844579/zodiac_images_refs/p2emtfj9e6ibbyzok09r.png"
    }

    @classmethod
    def _reload_env(cls):
        load_dotenv(override=True)

    @classmethod
    def _resolve_symbol(cls, neuro_pattern: Optional[str]) -> str:
        if not neuro_pattern:
            return "ankh"
        if neuro_pattern.startswith("Mixed"):
            return cls.NEURO_SYMBOL_MAP.get("Mixed", "ankh")
        return cls.NEURO_SYMBOL_MAP.get(neuro_pattern, "ankh")

    @classmethod
    def _resolve_colors(cls, zodiac_sign: Optional[str]) -> Dict[str, str]:
        if not zodiac_sign:
            return cls.DEFAULT_COLORS
        colors = cls.ZODIAC_COLORS.get(zodiac_sign)
        if colors: return colors
        for key, value in cls.ZODIAC_COLORS.items():
            if key.lower() == zodiac_sign.lower(): return value
        return cls.DEFAULT_COLORS

    @classmethod
    async def _generate_single_clip(cls, client, prompt_text: str, scene_idx: int, model: str, prompt_image: Optional[str] = None) -> str:
        """Helper to generate and poll a single video clip concurrently."""
        print(f"🎥 [Scene {scene_idx}] Generating cinematic animation...")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Use image-to-video if a valid image reference URL is provided
                if prompt_image and len(prompt_image.strip()) > 10:
                    print(f"🖼️ [Scene {scene_idx}] Using Image Reference for accuracy: {prompt_image[:30]}...")
                    task = await client.image_to_video.create(
                        model=model,
                        prompt_image=prompt_image.strip(),
                        prompt_text=prompt_text,
                        ratio="1280:720",
                        duration=8
                    )
                else:
                    print(f"📝 [Scene {scene_idx}] Using Text-to-Video mode.")
                    task = await client.text_to_video.create(
                        model=model,
                        prompt_text=prompt_text,
                        ratio="1280:720",
                        duration=8
                    )
                # Poll for completion
                while True:
                    task = await client.tasks.retrieve(task.id)
                    if task.status == "SUCCEEDED":
                        out = task.output
                        if isinstance(out, list) and len(out) > 0:
                            return out[0]
                        elif isinstance(out, dict):
                            return out.get("video")
                        return str(out)
                    elif task.status in ["PENDING", "THROTTLED"]:
                        print(f"⏳ [Scene {scene_idx}] Task is {task.status}... Waiting in queue.")
                    elif task.status in ["FAILED", "CANCELLED"]:
                        err = getattr(task, "error", f"Unknown error (Status: {task.status})")
                        raise Exception(f"Runway Task Failed [Scene {scene_idx}]: {err}")
                    
                    await asyncio.sleep(5)
                
                # If it didn't break due to THROTTLED, then it's done or errored elsewhere
                if task.status == "SUCCEEDED":
                    break
                    
            except Exception as e:
                if "429" in str(e) or "throttle" in str(e).lower():
                    print(f"⚠️ [Scene {scene_idx}] API Rate Limit (429)! Retrying... (Attempt {attempt+1}/{max_retries})")
                else:
                    raise
                    
            # If we reached here without returning, we need to retry. Wait before retrying.
            await asyncio.sleep(10)
        else:
            raise Exception(f"Runway Task Failed [Scene {scene_idx}]: Throttled repeatedly, exceeded max retries.")

    @classmethod
    async def _download_clip(cls, url: str, path: str) -> str:
        async with httpx.AsyncClient(timeout=120.0) as fetch_client:
            resp = await fetch_client.get(url)
            resp.raise_for_status()
            Path(path).write_bytes(resp.content)
            return path

    @classmethod
    async def _get_cached_video(cls, zodiac_sign: str, neuro_pattern: str) -> Optional[Dict[str, Any]]:
        """Check DB for a pre-generated video matching this (zodiac, neuro) combo."""
        from app.models.video_cache import VideoCache
        from sqlalchemy.future import select
        from sqlalchemy import update

        cache_zodiac = zodiac_sign or "default"
        cache_neuro = neuro_pattern or "default"

        async with async_session_maker() as session:
            result = await session.execute(
                select(VideoCache).where(
                    VideoCache.zodiac_sign == cache_zodiac,
                    VideoCache.neuro_pattern == cache_neuro
                )
            )
            cached = result.scalar_one_or_none()
            if cached:
                # Increment hit counter
                cached.hit_count += 1
                cached.last_used_at = datetime.utcnow()
                await session.commit()
                print(f"⚡ Cache HIT: {cache_zodiac}+{cache_neuro} (used {cached.hit_count} times)")
                return {
                    "status": "success",
                    "video_url": cached.video_url,
                    "video_path": None,
                    "session_dir": "cached",
                    "metadata": {
                        "symbol_key": cached.symbol_key,
                        "symbol_name_ar": cls.SYMBOLS.get(cached.symbol_key, {}).get("name_ar", ""),
                        "neuro_pattern": neuro_pattern,
                        "zodiac_sign": zodiac_sign,
                        "cache_hit": True,
                        "hit_count": cached.hit_count
                    },
                    "message": f"فيديو جاهز من الذاكرة الذكية ⚡ (استُخدم {cached.hit_count} مرة)"
                }
        return None

    @classmethod
    async def _save_video_to_cache(cls, zodiac_sign: str, neuro_pattern: str, symbol_key: str, video_url: str):
        """Save a newly generated video URL to the cache DB."""
        from app.models.video_cache import VideoCache
        cache_zodiac = zodiac_sign or "default"
        cache_neuro = neuro_pattern or "default"
        async with async_session_maker() as session:
            entry = VideoCache(
                zodiac_sign=cache_zodiac,
                neuro_pattern=cache_neuro,
                symbol_key=symbol_key,
                video_url=video_url,
                hit_count=1
            )
            session.add(entry)
            await session.commit()
            print(f"💾 Cache SAVED: {cache_zodiac}+{cache_neuro} → {video_url[:60]}...")

    @classmethod
    async def generate_full_video(
        cls,
        assessment_data: Dict[str, Any],
        output_dir: str = "videos",
        neuro_pattern: Optional[str] = None,
        zodiac_sign: Optional[str] = None,
        avatar: str = "",
        model: str = "veo3.1_fast",
        include_video: bool = True,
        **kwargs
    ) -> Dict[str, Any]:

        print("🎬 Starting Multi-Scene AI Video Generation...")

        # ── 1. CHECK CACHE FIRST ─────────────────────────────────────────────
        if include_video:
            cached = await cls._get_cached_video(zodiac_sign, neuro_pattern)
            if cached:
                return cached
            print("🔍 Cache MISS – generating new video...")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = Path(output_dir) / timestamp
        session_dir.mkdir(parents=True, exist_ok=True)

        try:
            symbol_key = cls._resolve_symbol(neuro_pattern)
            symbol_data = cls.SYMBOLS[symbol_key]
            color_data = cls._resolve_colors(zodiac_sign)

            print(f"✨ Symbol: {symbol_data['name_ar']}")
            print(f"🎨 Colors: bg={color_data['bg'][:20]}.. accent={color_data['accent']}")

            # Safety and relaxing vibe modifier to ensure non-scary, natural output
            relaxing_modifier = " Soothing, beautiful, and deeply relaxing to watch. Not scary, no creepy or uncanny elements, very natural and safe."

            # Format the 3 prompts
            formatted_prompts = [
                pt.format(
                    bg_color=color_data["bg"],
                    accent_color=color_data["accent"],
                    vibe_desc=color_data["vibe"] + relaxing_modifier
                ) for pt in symbol_data["video_prompts"]
            ]

            # ── Override Scene 1 with zodiac-specific constellation intro ──────
            zodiac_scene1 = cls.ZODIAC_SCENE1_PROMPTS.get(zodiac_sign)
            if zodiac_scene1:
                formatted_prompts[0] = zodiac_scene1.format(
                    bg_color=color_data["bg"],
                    accent_color=color_data["accent"],
                    vibe_desc=color_data["vibe"] + relaxing_modifier
                )
                print(f"✨ [Scene 1] Zodiac-specific intro: {zodiac_sign}")
            else:
                print(f"⚠️ [Scene 1] No zodiac override found for '{zodiac_sign}', using default symbol intro.")

            (session_dir / "script.txt").write_text(
                f"Symbol: {symbol_data['name_ar']}\nPrompts:\n" + "\n".join(formatted_prompts),
                encoding="utf-8"
            )

            video_url = None
            final_video_path = None

            if include_video:
                runway_key = await get_env_or_db("runway_api_key", "RUNWAYML_API_SECRET")
                if not runway_key:
                    raise Exception("RunwayML Key missing in configuration")

                from runwayml import AsyncRunwayML
                client = AsyncRunwayML(api_key=runway_key)
                
                # 1. Start generation of all 3 clips CONCURRENTLY to speed up queueing
                print("🚀 Launching 3 Runway tasks CONCURRENTLY to optimize queue time...")
                task_futures = []
                for i, prompt in enumerate(formatted_prompts):
                    # Determine Which Image to Use Based on Scene
                    scene_img = None
                    if i == 0:   # Scene 1: Zodiac Sign
                        scene_img = cls.ZODIAC_IMAGES_REF.get(zodiac_sign, "")
                    elif i == 1: # Scene 2: Egyptian Neuroscience Symbol
                        scene_img = symbol_data.get("prompt_image", "")
                        
                    task_futures.append(asyncio.create_task(cls._generate_single_clip(client, prompt, i+1, model, scene_img)))
                    # Stagger by 2 seconds
                    await asyncio.sleep(2)
                
                clip_urls = await asyncio.gather(*task_futures)
                
                print(f"✅ All 3 clips gathered concurrently: {clip_urls}")

                # 2. Download the clips concurrently
                print("📥 Downloading clips locally...")
                dl_tasks = []
                for i, url in enumerate(clip_urls):
                    local_path = str(session_dir / f"clip_{i+1}.mp4")
                    dl_tasks.append(cls._download_clip(url, local_path))
                
                downloaded_paths = await asyncio.gather(*dl_tasks)
                print("✅ Clips downloaded.")

                # 3. Concatenate using FFMPEG (copy codec, instantaneous)
                print("🎞️ Stitching fragments together...")
                list_file_path = session_dir / "clips.txt"
                with open(list_file_path, "w") as f:
                    for path in downloaded_paths:
                        f.write(f"file '{Path(path).name}'\n")

                final_video_path = str(session_dir / "final_journey.mp4")
                
                process = await asyncio.create_subprocess_exec(
                    "ffmpeg", "-y", "-f", "concat", "-safe", "0", 
                    "-i", str(list_file_path), "-c", "copy", final_video_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    print(f"⚠️ FFMPEG Error: {stderr.decode()}")
                    raise Exception("FFMPEG failed to stitch videos")
                
                print(f"✅ Final 30-second Video ready at: {final_video_path}")
                
                # Cloudinary Upload with Retries
                print("☁️ Uploading final video to Cloudinary...")
                cloudinary.config(
                    cloud_name=await get_env_or_db("cloudinary_cloud_name"),
                    api_key=await get_env_or_db("cloudinary_api_key"),
                    api_secret=await get_env_or_db("cloudinary_api_secret", "CLOUDINARY_API_SECRET")
                )
                
                max_upload_retries = 3
                video_url = None
                for attempt in range(max_upload_retries):
                    try:
                        # Run synchronous upload in thread to not block async loop
                        upload_res = await asyncio.to_thread(
                            cloudinary.uploader.upload,
                            final_video_path,
                            resource_type="video",
                            folder="bayt_al_hayat_final_journeys"
                        )
                        video_url = upload_res["secure_url"]
                        print(f"✅ Uploaded successfully: {video_url}")
                        break
                    except Exception as upload_err:
                        print(f"⚠️ Cloudinary Upload Attempt {attempt+1} failed: {upload_err}")
                        if attempt < max_upload_retries - 1:
                            wait_time = (attempt + 1) * 5
                            print(f"⏳ Waiting {wait_time}s before retry...")
                            await asyncio.sleep(wait_time)
                        else:
                            raise Exception(f"Cloudinary upload failed after {max_upload_retries} attempts: {upload_err}")

                # Save to DB cache for future users
                await cls._save_video_to_cache(zodiac_sign, neuro_pattern, symbol_key, video_url)

                # Clean up local storage
                print("🧹 Deleting local video segments to free space...")
                shutil.rmtree(session_dir, ignore_errors=True)

            return {
                "status": "success",
                "video_url": video_url,
                "video_path": final_video_path,
                "session_dir": str(session_dir),
                "metadata": {
                    "symbol_key": symbol_key,
                    "symbol_name_ar": symbol_data["name_ar"],
                    "neuro_pattern": neuro_pattern,
                    "zodiac_sign": zodiac_sign,
                    "cache_hit": False,
                },
                "message": "30-second multi-scene video generated successfully"
            }

        except Exception as e:
            print(f"❌ Video generation error: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "session_dir": str(session_dir)
            }
