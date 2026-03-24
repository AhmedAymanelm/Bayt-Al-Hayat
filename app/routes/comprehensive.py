from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
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


@router.post("/generate-video", response_model=Dict[str, Any])
async def generate_comprehensive_video(
    submission: ComprehensiveAnswers,
    payment_session_id: str,
    model: str = "gpt4o",
    voice: str = "nova",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate AI video combining psychology, neuroscience, and astrology analysis
    
    Args:
        submission: Complete user data for all three assessments
        payment_session_id: The Kashier session ID for the successful payment
        model: AI model for script generation (gpt4o, gpt4, gpt35)
        voice: Voice model for TTS (nova, alloy, shimmer)
    
    Returns:
        Dict with comprehensive analysis and video generation result
    
    Raises:
        HTTPException: If payment is not verified or generation fails
    """
    # 1. Verify Payment
    try:
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
                detail="Payment required for AI video generation. Please complete the payment first."
            )
            
        # 2. Proceed with Video Generation and AI Text Report Generation Concurrently
        video_data = await ComprehensiveService.analyze_all(
            name=submission.name,
            psychology_answers=submission.psychology_answers,
            neuroscience_answers=submission.neuroscience_answers,
            birth_date=submission.birth_date,
            birth_time=submission.birth_time,
            birth_place=submission.birth_place
        )
        
        # Start both Heavy API calls concurrently to save time
        video_task = asyncio.create_task(AIVideoService.generate_full_video(
            video_data,
            "videos/comprehensive",
            model=model,
            voice=voice
        ))
        
        report_task = asyncio.create_task(ComprehensiveService.generate_comprehensive_report(
            name=submission.name,
            psychology_result=video_data.get("psychology", {}),
            neuroscience_result=video_data.get("neuroscience", {}),
            astrology_result=video_data.get("astrology", {})
        ))
        
        video_result, report_result = await asyncio.gather(video_task, report_task)
        
        # Save to history
        history_entry = AssessmentHistory(
            user_id=current_user.id,
            assessment_type="comprehensive",
            input_data=submission.model_dump(),
            result_data={"analysis": video_data, "report": report_result, "video": video_result},
            video_url=video_result.get("video_url") if isinstance(video_result, dict) else None
        )
        db.add(history_entry)
        await db.commit()
        
        return {
            "analysis": video_data,
            "report": report_result,
            "video": video_result,
            "payment_order_id": payment.order_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comprehensive video generation failed: {str(e)}")


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
