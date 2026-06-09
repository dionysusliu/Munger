"""Munger analysis API routes for Munger."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.source import Source
from app.models.wiki import WikiPage
from app.models.munger import MungerAnalysis
from app.schemas.munger import MungerAnalysisResponse, MungerDimensionInfo

router = APIRouter()


# ---------------------------------------------------------------------------
# Munger 12 Dimensions Data
# ---------------------------------------------------------------------------

MUNGER_DIMENSIONS = [
    MungerDimensionInfo(
        number=1,
        key="source",
        name="来源分析",
        name_en="Source Analysis",
        description="Analyze the provenance, credibility, and context of the source material.",
        questions=[
            "Who created this source and what are their credentials?",
            "What is the publication context and potential biases?",
            "When was this published and is it still relevant?",
            "What is the primary purpose of this source?",
        ],
    ),
    MungerDimensionInfo(
        number=2,
        key="claim",
        name="命题提取",
        name_en="Claim Extraction",
        description="Identify core claims, their types, and assess their strength.",
        questions=[
            "What are the main claims being made?",
            "Are these claims factual, normative, or predictive?",
            "What evidence supports each claim?",
            "How strong is the logical reasoning?",
        ],
    ),
    MungerDimensionInfo(
        number=3,
        key="concept",
        name="概念识别",
        name_en="Concept Identification",
        description="Extract key concepts with definitions and relationships.",
        questions=[
            "What are the key concepts introduced or used?",
            "How are these concepts defined?",
            "What are the relationships between concepts?",
            "Which concepts are novel vs. well-established?",
        ],
    ),
    MungerDimensionInfo(
        number=4,
        key="model",
        name="普世模型",
        name_en="Universal Model",
        description="Map insights to interdisciplinary mental models and frameworks.",
        questions=[
            "What mental models apply to this situation?",
            "Which disciplines offer relevant frameworks?",
            "How can first principles thinking be applied?",
            "What analogies from other domains illuminate this?",
        ],
    ),
    MungerDimensionInfo(
        number=5,
        key="mechanism",
        name="机制分析",
        name_en="Mechanism Analysis",
        description="Trace causal chains, feedback loops, and threshold effects.",
        questions=[
            "What are the causal relationships described?",
            "Are there feedback loops (positive or negative)?",
            "What are the key variables and their thresholds?",
            "What second and third-order effects exist?",
        ],
    ),
    MungerDimensionInfo(
        number=6,
        key="incentive",
        name="激励映射",
        name_en="Incentive Mapping",
        description="Identify stakeholders, incentives, and principal-agent dynamics.",
        questions=[
            "Who are the key stakeholders?",
            "What are their incentives (financial, social, psychological)?",
            "Are there principal-agent problems?",
            "What behaviors do the current incentives produce?",
        ],
    ),
    MungerDimensionInfo(
        number=7,
        key="psychology",
        name="心理误判",
        name_en="Psychology Check",
        description="Scan for cognitive biases from Munger's 25-standard-causes framework.",
        questions=[
            "What cognitive biases might be present?",
            "Is the author or subject falling into psychological misjudgment?",
            "Are there social proof, authority, or reciprocity effects?",
            "What incentives are creating biased thinking?",
        ],
    ),
    MungerDimensionInfo(
        number=8,
        key="dual_track",
        name="双轨分析",
        name_en="Dual-Track Analysis",
        description="Compare rational vs. psychological explanations for behavior.",
        questions=[
            "What is the rational explanation for the behavior?",
            "What is the psychological explanation?",
            "When do the two tracks diverge?",
            "Which track provides a better prediction?",
        ],
    ),
    MungerDimensionInfo(
        number=9,
        key="counterargument",
        name="反方观点",
        name_en="Counterargument",
        description="Identify strongest objections and falsifying evidence.",
        questions=[
            "What is the strongest argument against the main claims?",
            "What evidence would falsify the key conclusions?",
            "What are the limitations of the analysis?",
            "What would a smart opponent say?",
        ],
    ),
    MungerDimensionInfo(
        number=10,
        key="checklist",
        name="检查清单",
        name_en="Checklist",
        description="Apply a structured validation checklist.",
        questions=[
            "Have all major dimensions been considered?",
            "Are there any blind spots in the analysis?",
            "What base rates and priors should be applied?",
            "What is the confidence level and why?",
        ],
    ),
    MungerDimensionInfo(
        number=11,
        key="case",
        name="案例分析",
        name_en="Case Study",
        description="Find historical cases that validate or refute the analysis.",
        questions=[
            "What historical cases support this analysis?",
            "What cases contradict it?",
            "What can be learned from analogous situations?",
            "What is the base rate for similar outcomes?",
        ],
    ),
    MungerDimensionInfo(
        number=12,
        key="decision",
        name="决策复盘",
        name_en="Decision Review",
        description="Document in decision journal format for future review.",
        questions=[
            "What decision was made or should be made?",
            "What was the reasoning process?",
            "What were the alternatives considered?",
            "How will we know if this was the right decision?",
        ],
    ),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_source_or_404(db: AsyncSession, source_id: int) -> Source:
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return source


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/analyze/{source_id}", status_code=status.HTTP_202_ACCEPTED)
async def analyze_source(
    source_id: int,
    dimensions: Optional[list[int]] = None,
    db: AsyncSession = Depends(get_db),
):
    """Run Munger analysis on a source.

    Optionally specify which dimensions (1-12) to analyze. If not provided,
    all 12 dimensions are analyzed. Returns 202 Accepted immediately; the
    actual analysis runs asynchronously.
    """
    source = await _get_source_or_404(db, source_id)

    # Validate dimension numbers
    if dimensions:
        invalid = [d for d in dimensions if d < 1 or d > 12]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid dimension numbers: {invalid}. Must be 1-12.",
            )
        dims_to_analyze = [d for d in MUNGER_DIMENSIONS if d.number in dimensions]
    else:
        dims_to_analyze = MUNGER_DIMENSIONS

    # Check if source has content to analyze
    if not source.content_text and not source.content_summary:
        raise HTTPException(
            status_code=400,
            detail="Source has no extractable content for analysis",
        )

    # For now, create placeholder analysis records.
    # The actual LLM-powered analysis will be performed by a background worker.
    for dim in dims_to_analyze:
        # Check if analysis for this dimension already exists
        existing = await db.execute(
            select(MungerAnalysis)
            .where(MungerAnalysis.source_id == source_id)
            .where(MungerAnalysis.dimension_number == dim.number)
        )
        if existing.scalar_one_or_none():
            continue

        analysis = MungerAnalysis(
            source_id=source_id,
            dimension=dim.key,
            dimension_number=dim.number,
            analysis_content=f"Analysis for '{dim.name_en}' pending. "
                             f"Source: {source.title}. "
                             f"This analysis will be populated by the background worker.",
            confidence=0.0,
            key_insights="[]",
        )
        db.add(analysis)

    # Update source status if it was completed
    if source.status == "completed":
        source.status = "analyzing"

    # Log
    from app.models.log import IngestionLog
    db.add(IngestionLog(
        source_id=source_id,
        log_type="analysis",
        action="munger_analysis_triggered",
        details=f"Munger analysis triggered for source {source_id}, "
                f"dimensions: {[d.number for d in dims_to_analyze]}",
    ))

    return {
        "message": "Munger analysis triggered",
        "source_id": source_id,
        "dimensions": [
            {"number": d.number, "key": d.key, "name": d.name_en}
            for d in dims_to_analyze
        ],
        "status": "pending",
    }


@router.get("/analysis/{wiki_page_id}")
async def get_page_analysis(
    wiki_page_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get Munger analysis results for a wiki page."""
    # Verify page exists
    page = await db.get(WikiPage, wiki_page_id)
    if not page:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wiki page not found")

    # Get analyses
    result = await db.execute(
        select(MungerAnalysis)
        .where(MungerAnalysis.wiki_page_id == wiki_page_id)
        .order_by(MungerAnalysis.dimension_number)
    )
    analyses = result.scalars().all()

    # Group by dimension
    dimension_results = []
    for dim in MUNGER_DIMENSIONS:
        analysis = next(
            (a for a in analyses if a.dimension_number == dim.number), None
        )
        dimension_results.append({
            "dimension": {
                "number": dim.number,
                "key": dim.key,
                "name": dim.name,
                "name_en": dim.name_en,
                "description": dim.description,
            },
            "analysis": {
                "id": analysis.id,
                "analysis_content": analysis.analysis_content,
                "confidence": analysis.confidence,
                "key_insights": analysis.key_insights,
                "created_at": analysis.created_at,
            } if analysis else None,
        })

    return {
        "wiki_page_id": wiki_page_id,
        "wiki_page_title": page.title,
        "dimensions_completed": sum(1 for a in analyses if a.confidence > 0),
        "dimensions_total": 12,
        "dimensions": dimension_results,
    }


@router.get("/dimensions")
async def get_dimensions() -> list[MungerDimensionInfo]:
    """Return all 12 Munger dimensions with names, descriptions, and questions."""
    return MUNGER_DIMENSIONS


@router.get("/summary/{source_id}")
async def get_analysis_summary(
    source_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a summary dashboard of Munger analysis for a source.

    Returns completion status, confidence scores, and key insights
    across all 12 dimensions.
    """
    source = await _get_source_or_404(db, source_id)

    # Get all analyses for this source
    result = await db.execute(
        select(MungerAnalysis)
        .where(MungerAnalysis.source_id == source_id)
        .order_by(MungerAnalysis.dimension_number)
    )
    analyses = result.scalars().all()

    # Build dimension summary
    dim_summaries = []
    overall_confidence = 0.0
    completed_count = 0

    for dim in MUNGER_DIMENSIONS:
        analysis = next(
            (a for a in analyses if a.dimension_number == dim.number), None
        )
        if analysis and analysis.confidence > 0:
            completed_count += 1
            overall_confidence += analysis.confidence

        dim_summaries.append({
            "number": dim.number,
            "key": dim.key,
            "name": dim.name,
            "name_en": dim.name_en,
            "status": "completed" if (analysis and analysis.confidence > 0) else "pending",
            "confidence": analysis.confidence if analysis else 0.0,
            "insight_count": len(analysis.key_insights.split(","))
            if analysis and analysis.key_insights and analysis.key_insights != "[]"
            else 0,
        })

    avg_confidence = overall_confidence / completed_count if completed_count > 0 else 0.0

    return {
        "source_id": source_id,
        "source_title": source.title,
        "completion": {
            "completed": completed_count,
            "total": 12,
            "percentage": round(completed_count / 12 * 100, 1),
        },
        "overall_confidence": round(avg_confidence, 3),
        "dimensions": dim_summaries,
        "key_insights_all": [
            {
                "dimension": a.dimension,
                "dimension_number": a.dimension_number,
                "insights": a.key_insights,
            }
            for a in analyses
            if a.key_insights and a.key_insights != "[]"
        ],
    }
