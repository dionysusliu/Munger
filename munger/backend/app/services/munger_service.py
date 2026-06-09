"""Munger service - 12-dimension analysis workflow implementation.

Implements Charlie Munger's multi-disciplinary thinking framework:
Source, Claim, Concept, Universal Model, Mechanism, Incentive,
Psychology, Dual-Track, Counterargument, Checklist, Case Study, Decision Review.
"""

import json
import logging
from typing import Optional

from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload

from app.core.database import async_session_maker
from app.models.source import Source
from app.models.munger import MungerAnalysis
from app.models.wiki import WikiPage
from app.schemas.munger import MungerAnalysisResponse, MungerDimensionInfo
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class MungerService:
    """Orchestrates the Munger 12-dimension analysis workflow."""

    DIMENSIONS = [
        {
            "number": 1,
            "key": "source",
            "name": "来源",
            "name_en": "Source",
            "description": "Analyze the provenance and credibility of information",
            "questions": [
                "这段文字来自哪里？",
                "作者是谁？",
                "文本类型是什么？",
                "它的可信度如何？",
            ],
        },
        {
            "number": 2,
            "key": "claim",
            "name": "命题",
            "name_en": "Claim",
            "description": "Extract and classify core claims",
            "questions": [
                "核心命题是什么？",
                "命题类型是什么？",
                "适用条件是什么？",
            ],
        },
        {
            "number": 3,
            "key": "concept",
            "name": "概念",
            "name_en": "Concept",
            "description": "Identify and define key concepts",
            "questions": [
                "关键概念有哪些？",
                "如何定义？",
                "与相近概念的区别？",
            ],
        },
        {
            "number": 4,
            "key": "model",
            "name": "普世模型",
            "name_en": "Universal Model",
            "description": "Map to interdisciplinary mental models",
            "questions": [
                "背后有什么普世模型？",
                "来自哪个学科？",
                "适用边界是什么？",
            ],
        },
        {
            "number": 5,
            "key": "mechanism",
            "name": "机制",
            "name_en": "Mechanism",
            "description": "Trace causal chains and feedback loops",
            "questions": [
                "A为什么导致B？",
                "有哪些反馈回路？",
                "有没有临界点？",
            ],
        },
        {
            "number": 6,
            "key": "incentive",
            "name": "激励",
            "name_en": "Incentive",
            "description": "Map stakeholders, incentives, and principal-agent dynamics",
            "questions": [
                "有哪些利益主体？",
                "激励是否一致？",
                "有没有道德风险？",
            ],
        },
        {
            "number": 7,
            "key": "psychology",
            "name": "心理误判",
            "name_en": "Psychology",
            "description": "Check for cognitive biases",
            "questions": [
                "有哪些心理误判倾向在起作用？",
                "多因素叠加效应？",
            ],
        },
        {
            "number": 8,
            "key": "dual_track",
            "name": "双轨分析",
            "name_en": "Dual-Track",
            "description": "Rational vs psychological explanations",
            "questions": [
                "理性结构由哪些变量主导？",
                "心理结构受哪些潜意识影响？",
            ],
        },
        {
            "number": 9,
            "key": "counterargument",
            "name": "反方观点",
            "name_en": "Counterargument",
            "description": "Strongest objections and falsifying evidence",
            "questions": [
                "最强的反方观点是什么？",
                "哪些事实会推翻我的观点？",
            ],
        },
        {
            "number": 10,
            "key": "checklist",
            "name": "检查清单",
            "name_en": "Checklist",
            "description": "Structured validation checklist",
            "questions": [
                "是否区分了事实、解释和叙事？",
                "是否在能力圈内？",
            ],
        },
        {
            "number": 11,
            "key": "case",
            "name": "案例",
            "name_en": "Case Study",
            "description": "Historical cases that validate or refute",
            "questions": [
                "模型在哪个案例中出现？",
                "能否迁移到其他领域？",
            ],
        },
        {
            "number": 12,
            "key": "decision",
            "name": "决策复盘",
            "name_en": "Decision Review",
            "description": "Decision journal format",
            "questions": [
                "基于什么信息做判断？",
                "错在哪里？下次更新什么？",
            ],
        },
    ]

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service

    # ------------------------------------------------------------------
    # Dimension info
    # ------------------------------------------------------------------

    def get_dimensions_info(self) -> list[dict]:
        """Return metadata about all 12 Munger dimensions."""
        return [dim.copy() for dim in self.DIMENSIONS]

    # ------------------------------------------------------------------
    # Analysis orchestration
    # ------------------------------------------------------------------

    async def analyze_source(
        self,
        source_id: int,
        dimensions: list[int] | None = None,
    ) -> list[MungerAnalysis]:
        """Run Munger analysis on a source across specified dimensions.

        Args:
            source_id: The source to analyze.
            dimensions: List of dimension numbers (1-12) to run.
                        If None, runs all 12 dimensions.

        Returns:
            List of MungerAnalysis records created.
        """
        if not self.llm_service:
            logger.warning("No LLM service available for Munger analysis")
            return []

        # Get source
        async with async_session_maker() as session:
            result = await session.execute(
                select(Source).where(Source.id == source_id)
            )
            source = result.scalar_one_or_none()

        if not source:
            logger.error(f"Source {source_id} not found for Munger analysis")
            return []

        if not source.content_text:
            logger.error(f"Source {source_id} has no extracted text")
            return []

        # Determine which dimensions to analyze
        dim_numbers = dimensions or list(range(1, 13))
        dim_map = {d["number"]: d for d in self.DIMENSIONS}

        analyses = []
        for dim_num in dim_numbers:
            if dim_num not in dim_map:
                logger.warning(f"Invalid dimension number: {dim_num}")
                continue

            dimension = dim_map[dim_num]
            try:
                analysis = await self.analyze_dimension(
                    source_id, dimension, source.content_text
                )
                if analysis:
                    analyses.append(analysis)
            except Exception as e:
                logger.error(f"Dimension {dim_num} analysis failed: {e}")
                # Continue with remaining dimensions

        logger.info(f"Completed Munger analysis for source {source_id}: "
                    f"{len(analyses)}/{len(dim_numbers)} dimensions")
        return analyses

    async def analyze_dimension(
        self,
        source_id: int,
        dimension: dict,
        text: str,
    ) -> MungerAnalysis | None:
        """Analyze a single dimension for a source.

        Args:
            source_id: The source ID.
            dimension: Dimension metadata dict.
            text: The source text to analyze.

        Returns:
            The created MungerAnalysis record, or None if analysis failed.
        """
        if not self.llm_service:
            return None

        dim_key = dimension["key"]
        dim_number = dimension["number"]
        questions = dimension["questions"]

        # Check if analysis already exists
        async with async_session_maker() as session:
            existing = await session.execute(
                select(MungerAnalysis).where(
                    MungerAnalysis.source_id == source_id,
                    MungerAnalysis.dimension == dim_key,
                )
            )
            if existing.scalar_one_or_none():
                logger.debug(
                    f"Dimension {dim_key} already analyzed for source {source_id}"
                )
                # Delete old analysis to re-run
                old = existing.scalar_one()
                await session.delete(old)
                await session.commit()

        # Run LLM analysis
        try:
            result = await self.llm_service.analyze_dimension(
                text=text,
                dimension=dimension["name_en"],
                questions=questions,
            )
        except Exception as e:
            logger.error(f"LLM analysis failed for dimension {dim_key}: {e}")
            result = {"analysis": "", "confidence": 0.0, "key_insights": []}

        analysis_text = result.get("analysis", "")
        confidence = result.get("confidence", 0.0)
        key_insights = result.get("key_insights", [])

        # Persist analysis
        async with async_session_maker() as session:
            analysis = MungerAnalysis(
                source_id=source_id,
                dimension=dim_key,
                dimension_number=dim_number,
                analysis_content=analysis_text,
                confidence=max(0.0, min(1.0, float(confidence))),
                key_insights=json.dumps(key_insights) if key_insights else None,
            )
            session.add(analysis)
            await session.commit()
            await session.refresh(analysis)

        logger.debug(
            f"Analyzed dimension {dim_key} for source {source_id} "
            f"(confidence: {confidence})"
        )
        return analysis

    # ------------------------------------------------------------------
    # Analysis retrieval
    # ------------------------------------------------------------------

    async def get_analysis_summary(self, source_id: int) -> dict:
        """Get a summary of all Munger analyses for a source.

        Returns a dashboard-friendly summary dict.
        """
        async with async_session_maker() as session:
            result = await session.execute(
                select(MungerAnalysis)
                .where(MungerAnalysis.source_id == source_id)
                .order_by(MungerAnalysis.dimension_number)
            )
            analyses = result.scalars().all()

            if not analyses:
                return {
                    "source_id": source_id,
                    "total_dimensions": 12,
                    "completed": 0,
                    "overall_confidence": 0.0,
                    "dimensions": [],
                }

            dim_results = []
            total_confidence = 0.0
            dim_map = {d["number"]: d for d in self.DIMENSIONS}

            for analysis in analyses:
                dim_info = dim_map.get(
                    analysis.dimension_number,
                    {
                        "name": analysis.dimension,
                        "name_en": analysis.dimension,
                        "key": analysis.dimension,
                    },
                )
                insights = []
                if analysis.key_insights:
                    try:
                        insights = json.loads(analysis.key_insights)
                    except json.JSONDecodeError:
                        insights = [analysis.key_insights]

                dim_results.append(
                    {
                        "number": analysis.dimension_number,
                        "key": analysis.dimension,
                        "name": dim_info["name"],
                        "name_en": dim_info["name_en"],
                        "confidence": analysis.confidence,
                        "analysis_preview": (
                            analysis.analysis_content[:200] + "..."
                            if len(analysis.analysis_content) > 200
                            else analysis.analysis_content
                        ),
                        "insights": insights,
                        "created_at": (
                            analysis.created_at.isoformat()
                            if analysis.created_at
                            else None
                        ),
                    }
                )
                total_confidence += analysis.confidence

            avg_confidence = total_confidence / len(analyses) if analyses else 0.0

            return {
                "source_id": source_id,
                "total_dimensions": 12,
                "completed": len(analyses),
                "overall_confidence": round(avg_confidence, 3),
                "dimensions": dim_results,
            }

    async def get_analysis_for_page(self, wiki_page_id: int) -> list[MungerAnalysis]:
        """Get all Munger analyses associated with a wiki page."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(MungerAnalysis)
                .where(MungerAnalysis.wiki_page_id == wiki_page_id)
                .order_by(MungerAnalysis.dimension_number)
            )
            return list(result.scalars().all())

    async def get_analysis_by_dimension(
        self, source_id: int, dimension_key: str
    ) -> MungerAnalysis | None:
        """Get a specific dimension analysis for a source."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(MungerAnalysis).where(
                    MungerAnalysis.source_id == source_id,
                    MungerAnalysis.dimension == dimension_key,
                )
            )
            return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Batch operations
    # ------------------------------------------------------------------

    async def delete_source_analyses(self, source_id: int) -> int:
        """Delete all Munger analyses for a source. Returns count deleted."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(MungerAnalysis).where(
                    MungerAnalysis.source_id == source_id
                )
            )
            analyses = result.scalars().all()
            count = len(analyses)

            for analysis in analyses:
                await session.delete(analysis)

            await session.commit()
            logger.info(f"Deleted {count} Munger analyses for source {source_id}")
            return count
