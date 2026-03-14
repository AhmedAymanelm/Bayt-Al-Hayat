from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.models import User
from app.auth.dependencies import get_current_user
from app.models.history import AssessmentHistory
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from ..models.astrology import AstrologyRequest, AstrologyResponse
from ..services.astrology_service import AstrologyService
from ..services.ai_video_service import AIVideoService
from ..services.video_analytics import VideoAnalytics
import asyncio
import json

router = APIRouter(prefix="/astrology", tags=["astrology"])


class VideoGenerationRequest(BaseModel):
    name: str
    birth_date: str
    day_type: str = "today"
    birth_time: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    model: str = Field(default="gpt4o", description="AI model: gpt4, gpt4o, gpt35")
    voice: str = Field(default="nova", description="Voice: alloy, echo, fable, onyx, nova, shimmer")
    speed: float = Field(default=0.95, ge=0.5, le=2.0)
    use_cache: bool = True
    include_video: bool = False
    avatar: str = Field(default="arabic_female", description="Avatar preset")


@router.post("/analyze", response_model=AstrologyResponse)
async def analyze_daily_horoscope(
    request: AstrologyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    تحليل البرج اليومي وإرجاع التحليل النفسي الشامل
    """
    try:
        result = await AstrologyService.analyze(request)
        
        # Save to history
        history_entry = AssessmentHistory(
            user_id=current_user.id,
            assessment_type="astrology",
            input_data=request.model_dump(),
            result_data=result.model_dump()
        )
        db.add(history_entry)
        await db.commit()
        
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/generate-video")
async def generate_astrology_video(
    request: VideoGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate AI video explanation of astrology analysis
    
    Supports multiple models, voices, and customization options
    """
    
    try:
        astro_request = AstrologyRequest(
            name=request.name,
            birth_date=request.birth_date,
            day_type=request.day_type,
            birth_time=request.birth_time,
            latitude=request.latitude,
            longitude=request.longitude
        )
        
        result = await AstrologyService.analyze(astro_request)
        result_dict = result.model_dump()
        
        video_result = await AIVideoService.generate_full_video(
            result_dict,
            model=request.model,
            voice=request.voice,
            speed=request.speed,
            use_cache=request.use_cache,
            include_video=request.include_video,
            avatar=request.avatar
        )
        
        # Save to history
        history_entry = AssessmentHistory(
            user_id=current_user.id,
            assessment_type="astrology",
            input_data=request.model_dump(),
            result_data={"analysis": result_dict, "video": video_result},
            video_url=video_result.get("final_video")
        )
        db.add(history_entry)
        await db.commit()
        
        return {
            "analysis": result_dict,
            "video": video_result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Video generation failed: {str(e)}"
        )


@router.post("/generate-video-stream")
async def generate_astrology_video_stream(
    request: VideoGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Stream video generation progress in real-time
    """
    
    async def event_stream():
        try:
            yield f"data: {json.dumps({'status': 'analyzing', 'progress': 10})}\n\n"
            
            astro_request = AstrologyRequest(
                name=request.name,
                birth_date=request.birth_date,
                day_type=request.day_type,
                birth_time=request.birth_time,
                latitude=request.latitude,
                longitude=request.longitude
            )
            
            result = await AstrologyService.analyze(astro_request)
            result_dict = result.model_dump()
            
            yield f"data: {json.dumps({'status': 'generating_script', 'progress': 30})}\n\n"
            
            video_result = await AIVideoService.generate_full_video(
                result_dict,
                model=request.model,
                voice=request.voice,
                speed=request.speed,
                use_cache=request.use_cache,
                include_video=request.include_video,
                avatar=request.avatar
            )
            
            # Save to history
            history_entry = AssessmentHistory(
                user_id=current_user.id,
                assessment_type="astrology",
                input_data=request.model_dump(),
                result_data={"analysis": result_dict, "video": video_result},
                video_url=video_result.get("final_video")
            )
            db.add(history_entry)
            await db.commit()
            
            yield f"data: {json.dumps({'status': 'complete', 'progress': 100, 'result': video_result})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/voices")
async def get_available_voices():
    """List all available voice options"""
    return {
        "voices": AIVideoService.VOICES,
        "default": "nova"
    }


@router.get("/models")
async def get_available_models():
    """List all available AI models"""
    return {
        "models": AIVideoService.MODELS,
        "default": "gpt4o"
    }


@router.get("/analytics/stats")
async def get_analytics_stats():
    """Get video generation analytics and statistics"""
    try:
        stats = VideoAnalytics.get_stats()
        return stats
    except Exception as e:
        return {
            "error": str(e),
            "total_generations": 0
        }


@router.post("/analytics/quality")
async def analyze_script_quality(script: Dict[str, str]):
    """Analyze quality metrics of a generated script"""
    try:
        text = script.get("script", "")
        if not text:
            raise HTTPException(status_code=400, detail="Script text required")
        
        quality = VideoAnalytics.analyze_quality(text)
        return quality
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
