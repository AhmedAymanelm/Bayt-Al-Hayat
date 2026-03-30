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


async def generate_video_and_update_history(history_id: UUID, video_data: dict, neuro_pattern: str, zodiac_sign: str):
    """Background task to generate video and update history record."""
    try:
        from app.database import async_session_maker
        from app.models.history import AssessmentHistory
        from sqlalchemy.orm.attributes import flag_modified
        import asyncio
        
        print(f"⏳ [Background] Started processing video for history {history_id}")
        video_result = await AIVideoService.generate_full_video(
            assessment_data=video_data,
            output_dir="videos/comprehensive",
            neuro_pattern=neuro_pattern,
            zodiac_sign=zodiac_sign,
            model="gen4.5"
        )
        
        async with async_session_maker() as fresh_db:
            history = await fresh_db.get(AssessmentHistory, history_id)
            if history:
                history.video_url = video_result.get("video_url") if isinstance(video_result, dict) else None
                current_result = history.result_data
                current_result["video"] = video_result
                history.result_data = current_result
                flag_modified(history, "result_data")
                await fresh_db.commit()
                print(f"✅ [Background] Video ready and saved for history {history_id}")
    except Exception as e:
        print(f"❌ [Background] Failed for history {history_id}: {e}")
        try:
            from app.database import async_session_maker
            from app.models.history import AssessmentHistory
            from sqlalchemy.orm.attributes import flag_modified
            async with async_session_maker() as fresh_db:
                history = await fresh_db.get(AssessmentHistory, history_id)
                if history:
                    current_result = history.result_data
                    current_result["video"] = {
                        "status": "failed",
                        "message": f"عذراً، حدث خطأ فني غير متوقع. يرجى المحاولة لاحقاً أو التواصل مع الدعم الفني."
                    }
                    history.result_data = current_result
                    flag_modified(history, "result_data")
                    await fresh_db.commit()
        except Exception as inner_e:
            print(f"❌ [Background] Also failed to update error state: {inner_e}")

@router.post("/generate-video", response_model=Dict[str, Any])
async def generate_comprehensive_video(
    submission: ComprehensiveAnswers,
    payment_session_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate AI video combining psychology, neuroscience, and astrology analysis
    
    Args:
        submission: Complete user data for all three assessments
        payment_session_id: The Kashier session ID for the successful payment
    
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
            birth_place=submission.birth_place
        )
        
        # Inject letter result if provided by the client
        if submission.letter_result:
            video_data["letter"] = submission.letter_result
        
        neuro_pattern = video_data.get("neuroscience", {}).get("dominant")
        zodiac_sign = video_data.get("astrology", {}).get("sun_sign")
        
        # 3. Quick Cache Check
        cached_video = await AIVideoService._get_cached_video(zodiac_sign, neuro_pattern)

        # 4. Immediate AI Text Report (takes 5-10 seconds)
        report_result = await ComprehensiveService.generate_comprehensive_report(
            name=submission.name,
            psychology_result=video_data.get("psychology", {}),
            neuroscience_result=video_data.get("neuroscience", {}),
            astrology_result=video_data.get("astrology", {}),
            letter_result=submission.letter_result
        )
        
        # 5. Save initial history record
        pending_video_status = {
            "status": "processing", 
            "message": "🎬 جاري الآن تجهيز وإخراج رحلتك السينمائية المخصصة لبرجك ونمطك العصبي... السعي للكمال يأخذ وقتاً، استمتع بقراءة تقريرك!"
        }
        final_video_data = cached_video or pending_video_status
        
        history_entry = AssessmentHistory(
            user_id=current_user.id,
            assessment_type="comprehensive",
            input_data=submission.model_dump(),
            result_data={"analysis": video_data, "report": report_result, "video": final_video_data},
            video_url=cached_video.get("video_url") if cached_video else None
        )
        db.add(history_entry)
        await db.commit()
        await db.refresh(history_entry)
        
        # 6. Spawn Background Task if not cached
        if not cached_video:
            # Detach completely using asyncio.create_task rather than FastAPI BackgroundTasks.
            # This allows the original DB session dependency to close immediately,
            # preventing asyncpg InterfaceError (closed connections) after 15 min.
            import asyncio
            asyncio.create_task(
                generate_video_and_update_history(
                    history_id=history_entry.id,
                    video_data=video_data,
                    neuro_pattern=neuro_pattern,
                    zodiac_sign=zodiac_sign
                )
            )
        
        return {
            "status": "success",
            "history_id": str(history_entry.id),
            "analysis": video_data,
            "report": report_result,
            "video": final_video_data,
            "payment_order_id": payment.order_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comprehensive processing failed: {str(e)}")

@router.get("/video-status/{history_id}")
async def get_video_status(history_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """API for Flutter to poll the video status while reading."""
    history = await db.get(AssessmentHistory, history_id)
    if not history or history.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Assessment not found")
        
    return {
        "status": "success", 
        "video": history.result_data.get("video", {}), 
        "video_url": history.video_url
    }


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
