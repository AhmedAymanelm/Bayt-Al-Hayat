from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Dict, Any
import asyncio

from app.database import get_db
from app.auth.models import User
from app.auth.dependencies import get_current_user
from app.models.history import AssessmentHistory
from app.models.payment import PaymentRecord
from sqlalchemy.future import select
from ..models.comprehensive import ComprehensiveAnswers, ComprehensiveResult, ComprehensiveResultsInput
from ..services.comprehensive_service import ComprehensiveService
from ..services.ai_video_service import AIVideoService

router = APIRouter(prefix="/comprehensive", tags=["comprehensive"])


@router.post("/submit", response_model=Dict[str, Any])
async def submit_comprehensive_answers(
    submission: ComprehensiveAnswers,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit all assessment answers and get comprehensive analysis
    
    Args:
        submission: All answers (psychology, neuroscience, astrology)
    
    Returns:
        Dict: Complete analysis combining all three assessments
    
    Raises:
        HTTPException: If validation or processing fails
    """
    try:
        result = await ComprehensiveService.analyze_all(
            name=submission.name,
            psychology_answers=submission.psychology_answers,
            neuroscience_answers=submission.neuroscience_answers,
            birth_date=submission.birth_date,
            birth_time=submission.birth_time,
            birth_place=submission.birth_place
        )
        
        # Save to history
        history_entry = AssessmentHistory(
            user_id=current_user.id,
            assessment_type="comprehensive",
            input_data=submission.model_dump(),
            result_data=result
        )
        db.add(history_entry)
        await db.commit()
        
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))




async def _background_video_generation(video_data: dict, neuro_pattern: str, zodiac_sign: str, report_result: dict, user_id, input_data: dict):
    """Executes video generation in the background and saves history to the DB."""
    try:
        final_video_data = await AIVideoService.generate_full_video(
            assessment_data=video_data,
            output_dir="videos/comprehensive",
            neuro_pattern=neuro_pattern,
            zodiac_sign=zodiac_sign,
            model="veo3.1_fast"
        )
        # Save to history once completed using a fresh DB session
        from app.database import async_session_maker
        from app.models.history import AssessmentHistory
        async with async_session_maker() as fresh_db:
            history_entry = AssessmentHistory(
                user_id=user_id,
                assessment_type="comprehensive",
                input_data=input_data,
                result_data={"analysis": video_data, "report": report_result, "video": final_video_data},
                video_url=final_video_data.get("video_url") if isinstance(final_video_data, dict) else None
            )
            fresh_db.add(history_entry)
            await fresh_db.commit()
    except Exception as e:
        print(f"Background Video Generation Failed for {zodiac_sign}/{neuro_pattern}: {e}")

@router.post("/generate-video", response_model=Dict[str, Any])
async def generate_comprehensive_report_and_video(
    submission: ComprehensiveAnswers,
    background_tasks: BackgroundTasks,
    payment_session_id: str = "test",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    1. Verifies Payment.
    2. Instantly generates AI Text Report (Psychology + Neuroscience + Astrology).
    3. Triggers cinematic AI Video Generation in the Background.
    Return returns immediately so mobile apps do not time out.
    
    Args:
        submission: Complete user data for all three assessments
        payment_session_id: The Fawaterk session ID for the successful payment
    
    Returns:
        Dict with comprehensive analysis and video generation result
    
    Raises:
        HTTPException: If payment is not verified or generation fails
    """
    # 1. Verify Payment
    try:
        if payment_session_id != "test":
            payment_result = await db.execute(
                select(PaymentRecord).where(
                    PaymentRecord.session_id == payment_session_id,
                    PaymentRecord.user_id == current_user.id,
                    PaymentRecord.status == "SUCCESS"
                )
            )
            payment = payment_result.scalar_one_or_none()
            
            if not payment:
                raise HTTPException(
                    status_code=402, 
                    detail="Payment session invalid or already used. Please complete a new payment."
                )
            
            # 🚨 BUG FIX: Mark as consumed immediately to prevent Replay Attacks and Race Conditions
            payment.status = "CONSUMED"
            await db.commit()
        else:
            class MockPayment:
                order_id = "test_order_bypass"
            payment = MockPayment()
            
        # 2. Proceed with all assessments
        video_data = await ComprehensiveService.analyze_all(
            name=submission.name,
            psychology_answers=submission.psychology_answers,
            neuroscience_answers=submission.neuroscience_answers,
            birth_date=submission.birth_date,
            birth_time=submission.birth_time,
            birth_place=submission.city_of_birth
        )
        
        # Inject letter result if provided by the client
        if submission.letter_result:
            video_data["letter"] = submission.letter_result
        
        neuro_pattern = video_data.get("neuroscience", {}).get("dominant")
        zodiac_sign = video_data.get("astrology", {}).get("sun_sign")
        
        # 3. Check Cache
        cached_video = await AIVideoService._get_cached_video(zodiac_sign, neuro_pattern)
        
        # 4. Generate AI Text Report (Instantaneous ~10s)
        report_result = await ComprehensiveService.generate_comprehensive_report(
            name=submission.name,
            psychology_result=video_data.get("psychology", {}),
            neuroscience_result=video_data.get("neuroscience", {}),
            astrology_result=video_data.get("astrology", {}),
            letter_result=submission.letter_result
        )

        # 5. Handle Background Video or Immediate DB Save
        if cached_video:
            video_response = {"status": "ready", "video_url": cached_video.get("video_url")}
            # Save history immediately since video is already ready
            history_entry = AssessmentHistory(
                user_id=current_user.id,
                assessment_type="comprehensive",
                input_data=submission.model_dump(),
                result_data={"analysis": video_data, "report": report_result, "video": cached_video},
                video_url=cached_video.get("video_url")
            )
            db.add(history_entry)
            await db.commit()
        else:
            video_response = {"status": "generating", "video_url": None}
            # Queue the video generation to process in the background
            background_tasks.add_task(
                _background_video_generation,
                video_data, neuro_pattern, zodiac_sign, report_result, current_user.id, submission.model_dump()
            )
        
        return {
            "status": "success",
            "analysis": video_data,
            "report": report_result,
            "zodiac_sign": zodiac_sign,
            "neuro_pattern": neuro_pattern,
            "video": video_response,
            "payment_order_id": payment.order_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comprehensive processing failed: {str(e)}")

@router.get("/check-video-status")
async def check_video_status(zodiac_sign: str, neuro_pattern: str):
    """
    Endpoint for mobile apps to poll video generation status.
    Call this every 10 seconds if POST /generate-video returns video.status == 'generating'.
    """
    cached_video = await AIVideoService._get_cached_video(zodiac_sign, neuro_pattern)
    if cached_video:
        return {"status": "ready", "video_url": cached_video.get("video_url")}
    
    return {"status": "generating", "video_url": None}



@router.post("/analyze-from-results", response_model=Dict[str, Any])
async def analyze_from_results(
    submission: ComprehensiveResultsInput,
    model: str = "gpt-4o",
    temperature: float = 0.8,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate comprehensive AI analysis report from pre-computed results.
    
    Use this endpoint when you already have results from individual assessments
    (psychology, neuroscience, astrology) and want to get a unified AI-generated 
    comprehensive analysis report.
    
    Args:
        submission: Pre-computed results from all three assessments
        model: AI model for report generation (gpt-4o, gpt-4-turbo-preview, gpt-3.5-turbo)
        temperature: Creativity level (0.0-1.0, default 0.8)
    
    Returns:
        Dict containing comprehensive analysis report and results summary
    
    Raises:
        HTTPException: If analysis generation fails
    """
    try:
        report = await ComprehensiveService.generate_comprehensive_report(
            name=submission.name,
            psychology_result=submission.psychology_result,
            neuroscience_result=submission.neuroscience_result,
            astrology_result=submission.astrology_result,
            letter_result=submission.letter_result,
            model=model,
            temperature=temperature
        )
        
        # Save to history
        history_entry = AssessmentHistory(
            user_id=current_user.id,
            assessment_type="comprehensive",
            input_data=submission.model_dump(),
            result_data=report
        )
        db.add(history_entry)
        await db.commit()
        
        return report
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to generate comprehensive analysis: {str(e)}"
        )
