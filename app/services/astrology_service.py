import httpx
from datetime import datetime
from typing import Dict, Any, Optional
from ..models.astrology import AstrologyRequest, AstrologyResponse
from app.utils.settings_helper import get_env_or_db
class AstrologyService:
    """خدمة منطق الأعمال لعلم الفلك"""
    

    ASTROLOGY_API_BASE_DEFAULT = "https://json.freeastrologyapi.com"

    ZODIAC_SIGNS_AR = {
        "aries": "الحمل",
        "taurus": "الثور",
        "gemini": "الجوزاء",
        "cancer": "السرطان",
        "leo": "الأسد",
        "virgo": "العذراء",
        "libra": "الميزان",
        "scorpio": "العقرب",
        "sagittarius": "القوس",
        "capricorn": "الجدي",
        "aquarius": "الدلو",
        "pisces": "الحوت"
    }
    

    MOOD_TO_PSYCHOLOGICAL = {
        "Happy": "مستقر نفسياً مع شعور بالرضا والطمأنينة",
        "Sad": "يميل للتأمل والهدوء، قد تشعر ببعض الكآبة الخفيفة",
        "Anxious": "بعض التوتر الداخلي، تحتاج لممارسة التنفس العميق",
        "Energetic": "نشيط ومفعم بالحيوية النفسية والحماس",
        "Calm": "هادئ ومتزن نفسياً، حالة سلام داخلي",
        "Stressed": "ضغط نفسي ملحوظ، يحتاج لإدارة أفضل للتوتر",
        "Optimistic": "إيجابي ومتفائل، حالة نفسية مرتفعة",
        "Normal": "متوازن ومستقر بشكل عام"
    }
    
    @classmethod
    def get_zodiac_sign(cls, birth_date_str: str) -> str:
        """تحديد البرج من تاريخ الميلاد"""
        birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
        month = birth_date.month
        day = birth_date.day
        
        if (month == 3 and day >= 21) or (month == 4 and day <= 19):
            return "aries"
        elif (month == 4 and day >= 20) or (month == 5 and day <= 20):
            return "taurus"
        elif (month == 5 and day >= 21) or (month == 6 and day <= 20):
            return "gemini"
        elif (month == 6 and day >= 21) or (month == 7 and day <= 22):
            return "cancer"
        elif (month == 7 and day >= 23) or (month == 8 and day <= 22):
            return "leo"
        elif (month == 8 and day >= 23) or (month == 9 and day <= 22):
            return "virgo"
        elif (month == 9 and day >= 23) or (month == 10 and day <= 22):
            return "libra"
        elif (month == 10 and day >= 23) or (month == 11 and day <= 21):
            return "scorpio"
        elif (month == 11 and day >= 22) or (month == 12 and day <= 21):
            return "sagittarius"
        elif (month == 12 and day >= 22) or (month == 1 and day <= 19):
            return "capricorn"
        elif (month == 1 and day >= 20) or (month == 2 and day <= 18):
            return "aquarius"
        else:
            return "pisces"
    
    @classmethod
    async def fetch_horoscope(cls, sign: str, day: str, birth_date_str: str, 
                               birth_time: Optional[str] = None, 
                               latitude: Optional[float] = None, 
                               longitude: Optional[float] = None) -> Dict[str, Any]:
        """جلب بيانات البرج من Free Astrology API - western/planets باستخدام تاريخ ووقت الميلاد"""
        
        from datetime import datetime, timedelta
        

        birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
        

        can_calculate_ascendant = birth_time is not None and latitude is not None and longitude is not None
        

        if birth_time:
            try:
                time_parts = birth_time.split(":")
                birth_hour = int(time_parts[0])
                birth_minute = int(time_parts[1]) if len(time_parts) > 1 else 0
            except:
                birth_hour = 12
                birth_minute = 0
        else:
            birth_hour = 12
            birth_minute = 0
        

        if latitude is None:
            latitude = 30.0
        if longitude is None:
            longitude = 31.0
        

        if day == "today":
            target_date = datetime.now()
        elif day == "tomorrow":
            target_date = datetime.now() + timedelta(days=1)
        else:  # yesterday
            target_date = datetime.now() - timedelta(days=1)
        

        api_base = await get_env_or_db("astrology_api_base") or cls.ASTROLOGY_API_BASE_DEFAULT
        api_key = await get_env_or_db("astrology_api_key")
        
        url = f"{api_base}/western/planets"
        
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }
        

        payload = {
            "year": target_date.year,
            "month": target_date.month,
            "date": target_date.day,
            "hours": birth_hour,
            "minutes": birth_minute,
            "seconds": 0,
            "latitude": latitude,
            "longitude": longitude,
            "timezone": 2.0,
            "config": {
                "observation_point": "topocentric",
                "ayanamsha": "tropical",
                "language": "en"
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                

                if data and "output" in data:
                    planets_list = data["output"]
                    

                    planets_data = {}
                    for planet in planets_list:
                        planet_name = planet.get("planet", {}).get("en", "")
                        if planet_name in ["Sun", "Moon", "Mars", "Venus", "Mercury", "True Node", "Mean Node", "Ascendant"]:
                            zodiac = planet.get("zodiac_sign", {}).get("name", {}).get("en", "")
                            degree = planet.get("normDegree", 0)
                            planets_data[planet_name] = {
                                "zodiac": zodiac,
                                "degree": round(degree, 2)
                            }
                    

                    if "Sun" in planets_data:
                        sun_sign = planets_data["Sun"]["zodiac"].lower()
                        

                        description_parts = []
                        

                        if "Ascendant" in planets_data and can_calculate_ascendant:
                            asc_zodiac = planets_data['Ascendant']['zodiac']
                            description_parts.append(f"طالعك في {asc_zodiac} يحدد شخصيتك وكيف يراك الآخرون")
                        elif not can_calculate_ascendant:
                            description_parts.append("ملاحظة: الطالع يحتاج لوقت وموقع ميلاد دقيقين لحسابه")
                        

                        sun_zodiac = planets_data['Sun']['zodiac']
                        description_parts.append(f"الشمس في {sun_zodiac} تمثل جوهرك وهويتك الحقيقية")
                        

                        if "Moon" in planets_data:
                            moon_zodiac = planets_data['Moon']['zodiac']
                            description_parts.append(f"القمر في {moon_zodiac} يكشف عالمك العاطفي الداخلي")
                        

                        if "Mercury" in planets_data:
                            mercury_zodiac = planets_data['Mercury']['zodiac']
                            description_parts.append(f"عطارد في {mercury_zodiac} يؤثر على تواصلك وأفكارك")
                        

                        if "Venus" in planets_data:
                            venus_zodiac = planets_data['Venus']['zodiac']
                            description_parts.append(f"الزهرة في {venus_zodiac} تؤثر على علاقاتك وجمالياتك")
                        

                        if "Mars" in planets_data:
                            mars_zodiac = planets_data['Mars']['zodiac']
                            description_parts.append(f"المريخ في {mars_zodiac} يعزز طاقتك وحماسك")
                        

                        if "True Node" in planets_data:
                            node_zodiac = planets_data['True Node']['zodiac']
                            description_parts.append(f"العقدة الشمالية في {node_zodiac} توجه مسارك الروحي")
                        elif "Mean Node" in planets_data:
                            node_zodiac = planets_data['Mean Node']['zodiac']
                            description_parts.append(f"العقدة الشمالية في {node_zodiac} توجه مسارك الروحي")
                        
                        description = ". ".join(description_parts) + "."
                        
                        print(f"✅ API نجح - تم استخراج {len(planets_data)} كوكب")
                        

                        return {
                            "description": description,
                            "mood": cls._infer_mood_from_planets(planets_data),
                            "compatibility": cls._get_default_compatibility(sun_sign),
                            "lucky_number": str(cls._generate_lucky_number()),
                            "color": cls._get_lucky_color(sun_sign),
                            "planets": planets_data,
                            "planets_raw": planets_data,
                            "ascendant": planets_data.get("Ascendant", {}).get("zodiac", "")
                        }
                
                raise Exception("No Sun data in API response")
                
        except Exception as e:

            print(f"❌ API فشل: {str(e)}")
            raise
    
    @classmethod
    def _infer_mood_from_text(cls, text: str) -> str:
        """استنتاج الحالة المزاجية من النص"""
        if not text:
            return "Normal"
            
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["great", "excellent", "wonderful", "amazing", "fantastic", "positive"]):
            return "Happy"
        elif any(word in text_lower for word in ["energy", "active", "dynamic", "motivated", "enthusiastic"]):
            return "Energetic"
        elif any(word in text_lower for word in ["calm", "peace", "relax", "harmony", "balanced"]):
            return "Calm"
        elif any(word in text_lower for word in ["stress", "pressure", "tension", "worry", "difficult"]):
            return "Stressed"
        elif any(word in text_lower for word in ["optimistic", "hopeful", "bright", "promising"]):
            return "Optimistic"
        elif any(word in text_lower for word in ["careful", "cautious", "anxious", "concerned"]):
            return "Anxious"
        else:
            return "Normal"
    
    @classmethod
    def _get_default_compatibility(cls, sign: str) -> str:
        """التوافق الافتراضي لكل برج"""
        compatibility_map = {
            "aries": "الأسد",
            "taurus": "العذراء",
            "gemini": "الدلو",
            "cancer": "الحوت",
            "leo": "الحمل",
            "virgo": "الثور",
            "libra": "الجوزاء",
            "scorpio": "السرطان",
            "sagittarius": "الحمل",
            "capricorn": "الثور",
            "aquarius": "الجوزاء",
            "pisces": "السرطان"
        }
        return compatibility_map.get(sign, "الميزان")
    
    @classmethod
    def _generate_lucky_number(cls) -> int:
        """توليد رقم حظ عشوائي"""
        import random
        return random.randint(1, 9)
    
    @classmethod
    def _get_lucky_color(cls, sign: str) -> str:
        """اللون المحظوظ لكل برج"""
        color_map = {
            "aries": "أحمر",
            "taurus": "أخضر",
            "gemini": "أصفر",
            "cancer": "فضي",
            "leo": "ذهبي",
            "virgo": "أزرق داكن",
            "libra": "وردي",
            "scorpio": "عنابي",
            "sagittarius": "بنفسجي",
            "capricorn": "بني",
            "aquarius": "أزرق",
            "pisces": "أخضر بحري"
        }
        return color_map.get(sign, "أبيض")
    
    @classmethod
    def _get_opposite_sign(cls, sign: str) -> str:
        """الحصول على البرج المعاكس (180 درجة) - للعقدة الجنوبية"""
        opposite_signs = {
            "Aries": "Libra",
            "Taurus": "Scorpio",
            "Gemini": "Sagittarius",
            "Cancer": "Capricorn",
            "Leo": "Aquarius",
            "Virgo": "Pisces",
            "Libra": "Aries",
            "Scorpio": "Taurus",
            "Sagittarius": "Gemini",
            "Capricorn": "Cancer",
            "Aquarius": "Leo",
            "Pisces": "Virgo"
        }
        return opposite_signs.get(sign, "")
    
    @classmethod
    def _infer_mood_from_planets(cls, planets_data: Dict[str, Any]) -> str:
        """استنتاج الحالة المزاجية من مواقع الكواكب"""

        

        if "Mars" in planets_data:
            mars_sign = planets_data["Mars"]["zodiac"]
            if mars_sign in ["Aries", "Leo", "Sagittarius"]:
                return "Energetic"
        

        if "Venus" in planets_data:
            venus_sign = planets_data["Venus"]["zodiac"]
            if venus_sign in ["Taurus", "Libra"]:
                return "Calm"
        

        if "Moon" in planets_data:
            moon_sign = planets_data["Moon"]["zodiac"]
            if moon_sign in ["Cancer", "Pisces"]:
                return "Calm"
            elif moon_sign in ["Aries", "Leo"]:
                return "Optimistic"
        
        return "Normal"
    
    @classmethod
    def convert_to_psychological_analysis(cls, horoscope_data: Dict[str, Any]) -> Dict[str, str]:
        """تحويل البيانات الفلكية إلى تحليل نفسي عملي - ديناميكي من API"""
        

        description = horoscope_data.get("description", "")
        mood = horoscope_data.get("mood", "Normal")
        compatibility = horoscope_data.get("compatibility", "")
        lucky_number = horoscope_data.get("lucky_number", "")
        lucky_color = horoscope_data.get("color", "")
        planets_data = horoscope_data.get("planets_raw", {})
        

        psychological_state = cls._analyze_psychological_from_planets(planets_data)
        emotional_state = cls._analyze_emotional_from_planets(planets_data)
        mental_state = cls._analyze_mental_from_planets(planets_data)
        physical_state = cls._analyze_physical_from_planets(planets_data)
        luck_level = cls._analyze_luck_from_planets(planets_data)
        advice = cls._extract_advice(description)
        warning = cls._extract_warning(description)
        
        return {
            "psychological_state": psychological_state,
            "emotional_state": emotional_state,
            "mental_state": mental_state,
            "physical_state": physical_state,
            "luck_level": luck_level,
            "lucky_color": lucky_color,
            "lucky_number": str(lucky_number),
            "compatibility": compatibility,
            "advice": advice,
            "warning": warning
        }
    
    @classmethod
    def _analyze_psychological_from_planets(cls, planets: Dict[str, Any]) -> str:
        """تحليل الحالة النفسية من مواقع الكواكب - API Dynamic"""
        if not planets:
            return "حالة نفسية متوازنة"
        
        analysis = []
        

        if "Ascendant" in planets:
            asc_sign = planets["Ascendant"]["zodiac"]
            if asc_sign in ["Aries", "Leo", "Sagittarius"]:
                analysis.append("شخصية قوية وقيادية، تترك انطباعاً واثقاً")
            elif asc_sign in ["Cancer", "Scorpio", "Pisces"]:
                analysis.append("شخصية حساسة وعميقة، تبدو غامضة للآخرين")
            elif asc_sign in ["Gemini", "Libra", "Aquarius"]:
                analysis.append("شخصية اجتماعية وودودة، سهل التواصل معها")
            elif asc_sign in ["Taurus", "Virgo", "Capricorn"]:
                analysis.append("شخصية عملية ومستقرة، تبدو موثوقة")
        

        if "Sun" in planets:
            sun_sign = planets["Sun"]["zodiac"]
            if sun_sign in ["Leo", "Aries", "Sagittarius"]:
                analysis.append("ثقة عالية بالنفس وطاقة داخلية قوية")
            elif sun_sign in ["Cancer", "Pisces"]:
                analysis.append("حساسية نفسية وتأمل داخلي عميق")
        

        if "Moon" in planets:
            moon_sign = planets["Moon"]["zodiac"]
            if moon_sign in ["Cancer", "Scorpio", "Pisces"]:
                analysis.append("عمق عاطفي وحدس نفسي قوي")
            elif moon_sign in ["Aries", "Leo"]:
                analysis.append("حيوية نفسية واندفاع إيجابي")
        
        if analysis:
            return ". ".join(analysis)
        return "حالة نفسية متوازنة ومستقرة"
    
    @classmethod
    def _analyze_emotional_from_planets(cls, planets: Dict[str, Any]) -> str:
        """تحليل الحالة العاطفية من الكواكب - API Dynamic"""
        if not planets:
            return "حالة عاطفية متوازنة"
        

        if "Venus" in planets:
            venus_sign = planets["Venus"]["zodiac"]
            if venus_sign in ["Taurus", "Libra"]:
                return "استقرار عاطفي قوي، انسجام في العلاقات، قدرة على التعبير عن المشاعر"
            elif venus_sign in ["Aries", "Scorpio"]:
                return "عواطف متقدة وشغف قوي، احتياج للتعبير المباشر"
            elif venus_sign in ["Cancer", "Pisces"]:
                return "حساسية عاطفية عالية، تعاطف وحنان، احتياج للأمان العاطفي"
        

        if "Moon" in planets:
            moon_sign = planets["Moon"]["zodiac"]
            if moon_sign in ["Cancer", "Pisces"]:
                return "عواطف رقيقة ومشاعر عميقة، احتياج للحماية العاطفية"
        
        return "حالة عاطفية طبيعية ومتوازنة، علاقات مستقرة"
    
    @classmethod
    def _analyze_mental_from_planets(cls, planets: Dict[str, Any]) -> str:
        """تحليل الحالة الذهنية من الكواكب - API Dynamic"""
        if not planets:
            return "حالة ذهنية طبيعية"
        

        if "Mercury" in planets:
            mercury_sign = planets["Mercury"]["zodiac"]
            if mercury_sign in ["Gemini", "Virgo"]:
                return "تركيز عالي، وضوح ذهني ممتاز، قدرة تحليلية قوية، مهارات تواصل فعالة"
            elif mercury_sign in ["Aquarius", "Libra"]:
                return "تفكير مبتكر، قدرة على التحليل الموضوعي، أفكار إبداعية"
            elif mercury_sign in ["Aries", "Sagittarius"]:
                return "تفكير سريع وحاسم، قدرات قيادية ذهنية، اتخاذ قرارات جريء"
            else:
                mercury_sign_ar = cls.ZODIAC_SIGNS_AR.get(mercury_sign.lower(), mercury_sign)
                return f"نشاط ذهني جيد، عطارد في {mercury_sign_ar} يدعم التفكير المتوازن"
        
        return "حالة ذهنية طبيعية ومستقرة، قدرات معرفية متوازنة"
    
    @classmethod
    def _analyze_physical_from_planets(cls, planets: Dict[str, Any]) -> str:
        """تحليل الحالة الجسدية من الكواكب - API Dynamic"""
        if not planets:
            return "طاقة متوسطة"
        

        if "Mars" in planets:
            mars_sign = planets["Mars"]["zodiac"]
            if mars_sign in ["Aries", "Leo", "Sagittarius"]:
                return "طاقة جسدية مرتفعة جداً، حيوية ونشاط عالي، قدرة على التحمل البدني"
            elif mars_sign in ["Capricorn", "Taurus"]:
                return "طاقة مستقرة ومتحملة، قوة جسدية تدريجية، صبر بدني"
            elif mars_sign in ["Cancer", "Pisces"]:
                return "طاقة متقلبة، احتياج للراحة المتكررة، حساسية جسدية"
            else:
                mars_sign_ar = cls.ZODIAC_SIGNS_AR.get(mars_sign.lower(), mars_sign)
                return f"طاقة متوازنة، المريخ في {mars_sign_ar} يدعم النشاط المعتدل"
        
        return "طاقة متوسطة ومستقرة، حالة جسدية طبيعية"
    
    @classmethod
    def _analyze_luck_from_planets(cls, planets: Dict[str, Any]) -> str:
        """تحليل مستوى الحظ من الكواكب - API Dynamic"""
        if not planets:
            return "متوسط"
        
        luck_score = 0
        



        
        if "Sun" in planets:
            sun_sign = planets["Sun"]["zodiac"]
            if sun_sign in ["Leo", "Aries"]:
                luck_score += 2
        
        if "Venus" in planets:
            venus_sign = planets["Venus"]["zodiac"]
            if venus_sign in ["Taurus", "Libra", "Pisces"]:
                luck_score += 2
        
        if "Mars" in planets:
            mars_sign = planets["Mars"]["zodiac"]
            if mars_sign in ["Aries", "Scorpio"]:
                luck_score += 1
        
        if luck_score >= 4:
            return "مرتفع جداً - يوم استثنائي، فرص ذهبية متاحة، استغل اللحظة"
        elif luck_score >= 2:
            return "مرتفع - فرص جيدة متاحة، وقت مناسب للمبادرات الجديدة"
        elif luck_score >= 1:
            return "متوسط إلى جيد - فرص عادية، اعتمد على جهدك واجتهادك"
        else:
            return "متوسط - يوم عادي، ركز على الاستقرار والخطط المدروسة"
    
    @classmethod
    def _extract_advice(cls, description: str) -> str:
        """استخراج النصيحة من الوصف"""

        advice_parts = []
        
        if "الشمس" in description or "Sun" in description:
            advice_parts.append("ركز على هويتك الشخصية وأهدافك الرئيسية")
        
        if "القمر" in description or "Moon" in description:
            advice_parts.append("اهتم بمشاعرك واحتياجاتك العاطفية")
        
        if "المريخ" in description or "Mars" in description:
            advice_parts.append("استخدم طاقتك وحماسك بحكمة")
        
        if "الزهرة" in description or "Venus" in description:
            advice_parts.append("اعتني بعلاقاتك وجمالياتك")
        
        if "عطارد" in description or "Mercury" in description:
            advice_parts.append("انتبه لتواصلك وقراراتك")
        
        if "العقدة" in description or "Node" in description:
            advice_parts.append("اتبع مسارك الروحي ونموك الشخصي")
        
        if advice_parts:
            return ". ".join(advice_parts[:3]) + "."
        
        return "ركز على أولوياتك واتخذ قراراتك بحكمة"
    
    @classmethod
    def _extract_warning(cls, description: str) -> str:
        """استخراج التحذير بناءً على الكواكب"""
        keywords = description.lower()
        

        if "المريخ" in keywords or "mars" in keywords:
            if any(sign in keywords for sign in ["aries", "الحمل", "scorpio", "العقرب"]):
                return "كن حذراً من التسرع والانفعال الزائد اليوم"
        
        if "زحل" in keywords or "saturn" in keywords:
            return "احذر من الضغوط والتأخيرات، تحلى بالصبر"
        
        if "عطارد" in keywords or "mercury" in keywords:
            return "انتبه للتواصل والمعلومات، تحقق من التفاصيل"
        

        return "لا تحذيرات خاصة، يوم مناسب للتقدم بثقة"
    
    @classmethod
    async def analyze(cls, request: AstrologyRequest) -> AstrologyResponse:
        """تحليل البرج اليومي وإرجاع التحليل النفسي"""
        

        zodiac_sign_en = cls.get_zodiac_sign(request.birth_date)
        zodiac_sign_ar = cls.ZODIAC_SIGNS_AR[zodiac_sign_en]
        

        horoscope_data = await cls.fetch_horoscope(
            zodiac_sign_en, 
            request.day_type, 
            request.birth_date,
            request.birth_time,
            request.latitude,
            request.longitude
        )
        

        analysis = cls.convert_to_psychological_analysis(horoscope_data)
        

        ascendant = horoscope_data.get("ascendant", "")
        ascendant_ar = cls.ZODIAC_SIGNS_AR.get(ascendant.lower(), ascendant) if ascendant else ""
        

        return AstrologyResponse(
            name=request.name,
            sun_sign=zodiac_sign_ar,
            ascendant=ascendant_ar,
            birth_date=request.birth_date,
            day_type=request.day_type,
            **analysis
        )
