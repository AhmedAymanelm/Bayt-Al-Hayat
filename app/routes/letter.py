from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.models import User
from app.auth.dependencies import get_current_user
from app.models.history import AssessmentHistory

from ..models.letter import LetterAnalysisRequest, LetterAnalysisResponse, GuidanceDictionary
from ..services.letter_service import LetterService

router = APIRouter(prefix="/letter", tags=["letter"])


@router.post("/analyze", response_model=LetterAnalysisResponse)
async def analyze_letter(
    request: LetterAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    تحليل الاسم والعمر وحساب الحرف الحاكم والتوجيه المناسب
    
    Args:
        request: الاسم والعمر
    
    Returns:
        LetterAnalysisResponse: نتيجة التحليل مع التوجيه المناسب
    
    Raises:
        HTTPException: في حالة وجود خطأ في التحليل
    """
    try:
        result = LetterService.analyze(request)
        
        # Save to history
        history_entry = AssessmentHistory(
            user_id=current_user.id,
            assessment_type="letter",
            input_data=request.model_dump(),
            result_data=result.model_dump()
        )
        db.add(history_entry)
        await db.commit()
        
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/dictionary", response_model=GuidanceDictionary)
async def get_guidance_dictionary():
    """
    جلب قاموس التوجيهات الكامل (spiritual, behavioral, physical)
    
    Returns:
        GuidanceDictionary: قاموس التوجيهات الكامل
    """
    return LetterService.get_dictionary()
