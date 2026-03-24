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
                "Cinematic shot. Soft {accent_color} light emerges from complete {bg_color} darkness, slowly gathering momentum. Particles of glowing energy swirl dynamically, building a sense of deep anticipation. {vibe_desc}.",
                "Cinematic shot. The image animates to reveal a massive, glowing ancient Egyptian Ankh symbol standing gracefully at the center. Powerful rings of {accent_color} light pulse outward from the Ankh, filling the scene with immense life force and cosmic harmony. {vibe_desc}.",
                "Cinematic shot. The Ankh slowly dissolves into pure {accent_color} stardust, leaving behind a tranquil, infinitely peaceful atmosphere that instills extreme psychological comfort. {vibe_desc}."
            ]
        },
        "djed": {
            "name_ar": "عمود جد",
            "prompt_image": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1774325013/egyptian_symbols/q7szwspoudjnxsnxiekr.jpg",
            "video_prompts": [
                "Cinematic shot. The ground on a {bg_color} setting shakes softly. A glowing beam of {accent_color} light descends from above, anchoring firmly into the cinematic earth. {vibe_desc}.",
                "Cinematic shot. The image animates to show a glowing ancient Egyptian Djed pillar slowly standing upright in the center. {accent_color} light lines ascend heavily around the pillar, radiating immense grounding power and stability. {vibe_desc}.",
                "Cinematic shot. The Djed pillar merges into the ground, turning the entire surface into a solid, glowing {accent_color} foundation of absolute safety and calmness. {vibe_desc}."
            ]
        },
        "isis_knot": {
            "name_ar": "عقدة إيزيس",
            "prompt_image": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1774325362/egyptian_symbols/bqxlwovjitmq8mwsgubs.jpg",
            "video_prompts": [
                "Cinematic shot. Soft {accent_color} ribbons of ethereal energy flow elegantly across a {bg_color} background, tying themselves softly in the center. {vibe_desc}.",
                "Cinematic shot. The image animates to form a rich glowing ancient Egyptian Isis Knot symbol. A gentle circular light halo appears in its heart, projecting pure protective emotional warmth. {vibe_desc}.",
                "Cinematic shot. The Isis knot dissolves into a warm {accent_color} mist that gently envelops the screen like a comforting protective blanket. {vibe_desc}."
            ]
        },
        "was_scepter": {
            "name_ar": "صولجان الواس",
            "prompt_image": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1774325129/egyptian_symbols/tcblvoi4ydc0bnfdrahg.jpg",
            "video_prompts": [
                "Cinematic shot. A powerful electric spark of {accent_color} light ignites in the center of a {bg_color} void, crackling with intense majestic energy. {vibe_desc}.",
                "Cinematic shot. The image animates to show a majestic golden ancient Egyptian Was Scepter standing proudly. Pure {accent_color} magical energy ascends upward along the scepter from its forked base to its glowing head, radiating authority. {vibe_desc}.",
                "Cinematic shot. The scepter releases a powerful energy pulse outwards, turning the screen into a brilliant {accent_color} glow before settling into empowering absolute calm. {vibe_desc}."
            ]
        },
        "scarab": {
            "name_ar": "الجعران",
            "prompt_image": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1774325432/egyptian_symbols/lbedn0572f6rxhb7jf5d.jpg",
            "video_prompts": [
                "Cinematic shot. Dense, rich {bg_color} sand slowly swirls and gathers in the center of the frame, infused with raw {accent_color} magical light. {vibe_desc}.",
                "Cinematic shot. The image animates into a majestic ancient Egyptian Scarab beetle emerging from the cosmic sands. Its metallic wings unfurl slightly, glowing with {accent_color} light of rebirth and transformation. {vibe_desc}.",
                "Cinematic shot. The scarab opens completely, releasing a blinding flash of {accent_color} light that wipes the screen into a pure, renewing dawn, instilling profound comfort and new beginnings. {vibe_desc}."
            ]
        },
        "eye_of_horus": {
            "name_ar": "عين حورس",
            "prompt_image": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1774325968/egyptian_symbols/hircpygiu1px1hhzul92.jpg",
            "video_prompts": [
                "Cinematic shot. In a cosmic {bg_color} starfield, fine traces of {accent_color} celestial dust begin to spiral, drawing focus to the center. {vibe_desc}.",
                "Cinematic shot. The image animates into a fiercely glowing ancient Egyptian Eye of Horus suspended in space. It pulses with sharp, crystalline {accent_color} energy, emitting beams of protective vision and clarity. {vibe_desc}.",
                "Cinematic shot. The Eye of Horus flashes once, wrapping the entire scene in a protective {accent_color} light barrier that gently fades into absolute tranquility and perfect psychological safety. {vibe_desc}."
            ]
        },
        "lotus": {
            "name_ar": "زهرة اللوتس",
            "prompt_image": "https://res.cloudinary.com/dz0ljvg1j/image/upload/v1774325681/egyptian_symbols/aduqhwyyb792zwwq0rap.jpg",
            "video_prompts": [
                "Cinematic shot. A serene {bg_color} water-like energy surface ripples softly. Specks of {accent_color} light float upward towards the center. {vibe_desc}.",
                "Cinematic shot. The image animates to reveal a breathtaking ancient Egyptian Lotus flower blooming gracefully from the energy water. Its petals glow with a soft, restorative {accent_color} light, radiating purity. {vibe_desc}.",
                "Cinematic shot. The lotus dissolves into a shower of soft, glowing {accent_color} petals that gently fall across the screen, leaving a sensation of deep inner healing and peace. {vibe_desc}."
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
        
        # Use image-to-video ONLY for the core symbol scene (Scene 2) if an image is provided
        if prompt_image and scene_idx == 2:
            print(f"🖼️ [Scene {scene_idx}] Using Image Reference for accuracy.")
            task = await client.image_to_video.create(
                model=model,
                prompt_image=prompt_image,
                prompt_text=prompt_text,
                ratio="1280:720",
                duration=10
            )
        else:
            task = await client.text_to_video.create(
                model=model,
                prompt_text=prompt_text,
                ratio="1280:720",
                duration=10
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
            elif task.status in ["FAILED", "CANCELLED"]:
                err = getattr(task, "error", "Unknown error")
                raise Exception(f"Runway Task Failed [Scene {scene_idx}]: {err}")
            
            await asyncio.sleep(5)

    @classmethod
    async def _download_clip(cls, url: str, path: str) -> str:
        async with httpx.AsyncClient(timeout=120.0) as fetch_client:
            resp = await fetch_client.get(url)
            resp.raise_for_status()
            Path(path).write_bytes(resp.content)
            return path

    @classmethod
    async def generate_full_video(
        cls,
        assessment_data: Dict[str, Any],
        output_dir: str = "videos",
        neuro_pattern: Optional[str] = None,
        zodiac_sign: Optional[str] = None,
        avatar: str = "",
        model: str = "gen4.5", # Default to gen4.5 but using 5s duration clips
        include_video: bool = True,
        **kwargs
    ) -> Dict[str, Any]:

        print("🎬 Starting Multi-Scene AI Video Generation...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = Path(output_dir) / timestamp
        session_dir.mkdir(parents=True, exist_ok=True)

        try:
            symbol_key = cls._resolve_symbol(neuro_pattern)
            symbol_data = cls.SYMBOLS[symbol_key]
            color_data = cls._resolve_colors(zodiac_sign)

            print(f"✨ Symbol: {symbol_data['name_ar']}")
            print(f"🎨 Colors: bg={color_data['bg'][:20]}.. accent={color_data['accent']}")

            # Format the 3 prompts
            formatted_prompts = [
                pt.format(
                    bg_color=color_data["bg"],
                    accent_color=color_data["accent"],
                    vibe_desc=color_data["vibe"]
                ) for pt in symbol_data["video_prompts"]
            ]

            (session_dir / "script.txt").write_text(
                f"Symbol: {symbol_data['name_ar']}\nPrompts:\n" + "\n".join(formatted_prompts),
                encoding="utf-8"
            )

            video_url = None
            final_video_path = None

            if include_video:
                runway_key = os.getenv("RUNWAYML_API_SECRET")
                if not runway_key:
                    raise Exception("RUNWAYML_API_SECRET missing in environment variables")

                from runwayml import AsyncRunwayML
                client = AsyncRunwayML(api_key=runway_key)
                
                # 1. Start generation of all 3 clips concurrently
                print("🚀 Launching 3 Runway concurrent tasks...")
                tasks = [
                    cls._generate_single_clip(client, prompt, i+1, model, symbol_data.get("prompt_image"))
                    for i, prompt in enumerate(formatted_prompts)
                ]
                clip_urls = await asyncio.gather(*tasks)
                print(f"✅ All 3 clips gathered: {clip_urls}")

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
                
                # Cloudinary Upload to save local server space
                print("☁️ Uploading final video to Cloudinary...")
                cloudinary.config(
                    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
                    api_key=os.getenv("CLOUDINARY_API_KEY"),
                    api_secret=os.getenv("CLOUDINARY_API_SECRET")
                )
                
                # Run synchronous upload in thread to not block async loop
                upload_res = await asyncio.to_thread(
                    cloudinary.uploader.upload,
                    final_video_path,
                    resource_type="video",
                    folder="bayt_al_hayat_final_journeys"
                )
                video_url = upload_res["secure_url"]
                print(f"✅ Uploaded successfully: {video_url}")

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
