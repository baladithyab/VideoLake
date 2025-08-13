#!/usr/bin/env python3
"""
Streamlit App for S3 Vectors: Search, Temporal Search, Ingestion
- Calls only backend services in src/services (no direct AWS calls in UI)
- Safe-cost guardrails: "Use Real AWS" toggles default to OFF
- Documentation-first: final validation is server-side per .kiro/steering/mcp-documentation-first.md
- Friendly error handling with structured logging (no sensitive details exposed)
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional

import streamlit as st

# Ensure repo root is on sys.path so "import src.services..." resolves when running from repo root
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.append(_REPO_ROOT)

# Backend services (no direct AWS calls in UI)
from src.services.similarity_search_engine import (  # noqa: E402
    IndexType,
    SimilaritySearchEngine,
    TemporalFilter,
)
from src.services.video_embedding_storage import (  # noqa: E402
    VideoEmbeddingStorageService,
)
from src.utils.logging_config import (  # noqa: E402
    get_structured_logger,
    setup_logging,
)
# Unified Demo (default landing) - REMOVED: Now using comprehensive unified_streamlit_app.py
# from frontend.unified_demo import render_unified_demo

# Initialize structured logging once for the UI process
try:
    setup_logging(level="INFO", structured=True)
except Exception:
    # Fall back silently; Streamlit may have already configured logging
    pass

_logger = logging.getLogger("streamlit_app")
_slogger = get_structured_logger("streamlit_app")


def _safe_parse_json_object(raw: str) -> Optional[Dict[str, Any]]:
    """
    Safely parse a JSON string into a dict.
    Returns None if input is empty/whitespace or invalid or non-object.
    """
    if not raw or not raw.strip():
        return None
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _result_rows(results) -> List[Dict[str, Any]]:
    """
    Convert backend results into display rows with requested columns.
    """
    rows: List[Dict[str, Any]] = []
    for r in results or []:
        similarity = float(getattr(r, "similarity_score", 0.0) or 0.0)
        start_sec = getattr(r, "start_sec", None)
        end_sec = getattr(r, "end_sec", None)
        duration = None
        if isinstance(start_sec, (int, float)) and isinstance(end_sec, (int, float)):
            duration = float(end_sec) - float(start_sec)
        rows.append(
            {
                "vector_key": getattr(r, "key", ""),
                "content_type": getattr(r, "content_type", "unknown"),
                "similarity": round(similarity, 4),
                "distance": round(max(0.0, 1.0 - similarity), 4),
                "start_sec": start_sec,
                "end_sec": end_sec,
                "duration_sec": round(duration, 3) if duration is not None else None,
                "model_id": getattr(r, "model_id", None),
                "embedding_option": getattr(r, "embedding_option", None),
            }
        )
    return rows


def _header():
    st.title("S3 Vectors – Streamlit App")
    st.caption(
        "Documentation‑first UI. All model and parameter validation is enforced server‑side "
        "per .kiro/steering/mcp-documentation-first.md. No direct AWS calls are made from this UI."
    )


def _tab_search():
    st.subheader("Search")
    st.write("Search by text query against your S3 Vectors index.")

    index_arn = st.text_input(
        "Index ARN (required)",
        key="search_index_arn",
        help="arn:aws:s3vectors:region:account:bucket/…/index/…",
    )
    top_k = st.slider("Top K", min_value=1, max_value=50, value=10, step=1, key="search_topk")
    metadata_raw = st.text_area(
        "Metadata Filter (JSON, optional)",
        key="search_metadata",
        placeholder='{"content_type": "video"}',
        height=120,
        help="Optional JSON object. Invalid JSON will be ignored.",
    )
    use_real = getattr(st, "toggle", st.checkbox)(
        "Use Real AWS", value=False, key="search_real", help="Default OFF to avoid accidental costs."
    )
    query = st.text_input("Text Query", key="search_query")
    run = st.button("Run Search", type="primary", key="search_run")

    if not use_real:
        st.info("Use Real AWS is OFF. Enable it to run the search via backend services.", icon="🛡️")

    if not run:
        return
    if not use_real:
        return
    if not index_arn.strip():
        st.warning("Please provide an Index ARN.", icon="⚠️")
        return
    if not query.strip():
        st.warning("Please enter a Text Query.", icon="⚠️")
        return

    # Parse optional metadata filter
    metadata_filter = _safe_parse_json_object(metadata_raw)
    if metadata_raw.strip() and metadata_filter is None:
        st.warning("Metadata JSON invalid. Ignoring it.", icon="⚠️")

    correlation_id = f"ui_search_{int(time.time() * 1000)}"
    t0 = time.perf_counter()

    try:
        # Instantiate engine only when needed (avoid initializing AWS clients until required)
        engine = SimilaritySearchEngine()

        # Default to Marengo (multimodal) index type
        resp = engine.search_by_text_query(
            query_text=query,
            index_arn=index_arn,
            index_type=IndexType.MARENGO_MULTIMODAL,
            top_k=int(top_k),
            metadata_filters=metadata_filter,
        )

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        rows = _result_rows(resp.results)

        # Display results table
        try:
            import pandas as pd  # type: ignore

            st.dataframe(pd.DataFrame(rows), use_container_width=True)
        except Exception:
            st.dataframe(rows, use_container_width=True)

        # Non-sensitive timing and operation ID
        st.caption(f"Results: {resp.total_results} • Time: ~{int(elapsed_ms)} ms • Operation ID: {resp.query_id}")

        # Friendly suggestions (if any)
        if getattr(resp, "search_suggestions", None):
            with st.expander("Suggestions"):
                for s in resp.search_suggestions:
                    st.write(f"- {s}")

        # Structured logs
        _slogger.log_performance(
            operation="text_search",
            duration_ms=elapsed_ms,
            result_count=int(resp.total_results),
            top_k=int(top_k),
            correlation_id=correlation_id,
        )
        _slogger.log_operation(operation="text_search", level="INFO", op_id=resp.query_id, top_k=int(top_k))

    except Exception as e:
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        _slogger.log_error(
            operation="text_search",
            error=e,
            correlation_id=correlation_id,
            duration_ms=elapsed_ms,
        )
        st.error("Search failed. Please verify your inputs and try again. A correlation ID is provided below.")
        st.caption(f"Correlation ID: {correlation_id} • Time: ~{int(elapsed_ms)} ms")


def _parse_optional_float(s: str) -> Optional[float]:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return float(s)
    except Exception:
        return None


def _tab_temporal_search():
    st.subheader("Temporal Search")
    st.write("Search for scenes within a time window. Text query plus optional start/end seconds.")

    index_arn = st.text_input("Index ARN (required)", key="temp_index_arn")
    query = st.text_input("Text Query", key="temp_query")
    col1, col2 = st.columns(2)
    with col1:
        start_s = st.text_input("Start sec (optional)", key="temp_start")
    with col2:
        end_s = st.text_input("End sec (optional)", key="temp_end")

    top_k = st.slider("Top K", min_value=1, max_value=50, value=10, step=1, key="temp_topk")
    metadata_raw = st.text_area(
        "Metadata Filter (JSON, optional)",
        key="temp_metadata",
        placeholder='{"content_type": {"$in": ["video"]}}',
        height=120,
        help="Optional JSON object. Invalid JSON will be ignored.",
    )
    use_real = getattr(st, "toggle", st.checkbox)(
        "Use Real AWS", value=False, key="temp_real", help="Default OFF to avoid accidental costs."
    )
    run = st.button("Run Temporal Search", type="primary", key="temp_run")

    if not use_real:
        st.info("Use Real AWS is OFF. Enable it to run through backend services.", icon="🛡️")

    if not run:
        return
    if not use_real:
        return
    if not index_arn.strip():
        st.warning("Please provide an Index ARN.", icon="⚠️")
        return
    if not query.strip():
        st.warning("Please enter a Text Query.", icon="⚠️")
        return

    start_val = _parse_optional_float(start_s)
    end_val = _parse_optional_float(end_s)
    if (start_val is not None and end_val is not None) and (end_val < start_val):
        st.warning("End sec must be greater than or equal to Start sec.", icon="⚠️")
        return

    metadata_filter = _safe_parse_json_object(metadata_raw)
    if metadata_raw.strip() and metadata_filter is None:
        st.warning("Metadata Filter JSON is invalid. Ignoring it.", icon="⚠️")

    # Ensure video content type when using metadata-based path
    if metadata_filter is not None and "content_type" not in metadata_filter:
        metadata_filter["content_type"] = {"$in": ["video"]}

    correlation_id = f"ui_temporal_{int(time.time() * 1000)}"
    t0 = time.perf_counter()

    try:
        engine = SimilaritySearchEngine()

        # If metadata filter present or any temporal bound is provided, use flexible text path with TemporalFilter
        if metadata_filter is not None or (start_val is not None or end_val is not None):
            tf = (
                TemporalFilter(start_time=start_val, end_time=end_val)
                if (start_val is not None or end_val is not None)
                else None
            )
            resp = engine.search_by_text_query(
                query_text=query,
                index_arn=index_arn,
                index_type=IndexType.MARENGO_MULTIMODAL,
                top_k=int(top_k),
                temporal_filter=tf,
                metadata_filters=metadata_filter,
            )
        else:
            # Convenience API when no filters are set
            time_range = (start_val, end_val) if (start_val is not None and end_val is not None) else None
            resp = engine.search_video_scenes(
                video_query=query, index_arn=index_arn, time_range=time_range, top_k=int(top_k)
            )

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        rows = _result_rows(resp.results)

        try:
            import pandas as pd  # type: ignore

            st.dataframe(pd.DataFrame(rows), use_container_width=True)
        except Exception:
            st.dataframe(rows, use_container_width=True)

        st.caption(f"Results: {resp.total_results} • Time: ~{int(elapsed_ms)} ms • Operation ID: {resp.query_id}")

        _slogger.log_performance(
            operation="temporal_search",
            duration_ms=elapsed_ms,
            result_count=int(resp.total_results),
            top_k=int(top_k),
            correlation_id=correlation_id,
        )
        _slogger.log_operation(operation="temporal_search", level="INFO", op_id=resp.query_id, top_k=int(top_k))

    except Exception as e:
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        _slogger.log_error(
            operation="temporal_search",
            error=e,
            correlation_id=correlation_id,
            duration_ms=elapsed_ms,
        )
        st.error("Temporal search failed. Please verify inputs. A correlation ID is provided below.")
        st.caption(f"Correlation ID: {correlation_id} • Time: ~{int(elapsed_ms)} ms")


def _tab_ingestion():
    st.subheader("Ingestion")
    st.write(
        "Process a video via TwelveLabs and store embeddings in S3 Vectors. "
        "UI never uploads content; provide an S3 URI."
    )
    st.caption(
        "Final model/option validation is enforced server‑side. 'Use Real AWS' defaults OFF (cost guardrail)."
    )

    index_arn = st.text_input("Index ARN (required)", key="ing_index_arn")
    video_s3_uri = st.text_input(
        "Video Source S3 URI (required for real run)",
        key="ing_video_uri",
        placeholder="s3://your-bucket/path/to/video.mp4",
    )
    seg_seconds = st.slider("Segmentation seconds", min_value=2, max_value=10, value=5, step=1, key="ing_seg")
    embed_opts = st.multiselect(
        "Embedding options/models",
        options=["visual-text", "visual-image", "audio"],
        default=["visual-text"],
        key="ing_embed_opts",
        help="Options forwarded to backend. Validation occurs server-side.",
    )
    metadata_raw = st.text_area(
        "Optional metadata (JSON)",
        key="ing_metadata",
        placeholder='{"content_id": "movie-123", "title": "Example"}',
        height=120,
    )
    use_real = getattr(st, "toggle", st.checkbox)(
        "Use Real AWS", value=False, key="ing_real", help="Default OFF to avoid accidental costs."
    )
    run = st.button("Run Ingestion", type="primary", key="ing_run")

    if not use_real:
        st.info("Use Real AWS is OFF. Enable to run ingestion via backend services.", icon="🛡️")

    if not run:
        return
    if not use_real:
        return
    if not index_arn.strip():
        st.warning("Please provide an Index ARN.", icon="⚠️")
        return
    if not (video_s3_uri.strip().startswith("s3://")):
        st.warning("Please provide a valid S3 URI (s3://...).", icon="⚠️")
        return

    base_metadata = _safe_parse_json_object(metadata_raw)
    if metadata_raw.strip() and base_metadata is None:
        st.warning("Metadata JSON is invalid. Ignoring it.", icon="⚠️")

    correlation_id = f"ui_ingest_{int(time.time() * 1000)}"
    t0 = time.perf_counter()

    try:
        # Defer service creation until needed (avoid AWS clients until real run)
        service = VideoEmbeddingStorageService()
        result = service.process_video_end_to_end(
            video_s3_uri=video_s3_uri,
            index_arn=index_arn,
            embedding_options=embed_opts or ["visual-text"],
            use_fixed_length_sec=float(seg_seconds),
            base_metadata=base_metadata,
            key_prefix=None,
            cleanup_output=True,
        )

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        summary = (result or {}).get("summary") or {}
        storage = (result or {}).get("vector_storage") or {}
        success = summary.get("success", False)

        if success:
            st.success(
                f"Ingestion complete: {storage.get('stored_segments', 0)} segments • "
                f"{storage.get('total_vectors_stored', 0)} vectors.",
                icon="✅",
            )
            st.caption(f"Time: ~{int(elapsed_ms)} ms")

            failed = storage.get("failed_segments") or []
            if failed:
                st.warning(f"{len(failed)} segment(s) reported warnings/errors.", icon="⚠️")
                with st.expander("View failed segments (truncated)"):
                    try:
                        sample = failed[:25]
                        st.json(sample)
                    except Exception:
                        st.write(failed[:5])
        else:
            st.error("Ingestion failed. Please verify inputs. A correlation ID is provided below.", icon="❌")

        _slogger.log_performance(operation="ingestion", duration_ms=elapsed_ms, correlation_id=correlation_id)
        _slogger.log_operation(operation="ingestion", level="INFO", success=bool(success))

    except Exception as e:
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        _slogger.log_error(
            operation="ingestion",
            error=e,
            correlation_id=correlation_id,
            duration_ms=elapsed_ms,
        )
        st.error("Ingestion failed. Please verify inputs and try again. A correlation ID is provided below.")
        st.caption(f"Correlation ID: {correlation_id} • Time: ~{int(elapsed_ms)} ms")


def main():
    st.sidebar.title("Navigation")
    nav = st.sidebar.radio("Go to", ["Complete Pipeline", "Advanced Tools"], index=0, key="nav_choice")
    
    if nav == "Complete Pipeline":
        # Import and run the comprehensive unified Streamlit app
        try:
            from frontend.unified_streamlit_app import UnifiedStreamlitApp
            st.markdown("---")
            st.info("🎬 **Complete Pipeline Demo** - Full-featured video search experience")
            app = UnifiedStreamlitApp()
            app.run()
        except ImportError as e:
            st.error(f"Failed to load Complete Pipeline: {e}")
            st.info("Use the standalone launcher: `python frontend/launch_unified_streamlit.py`")
    else:
        _header()
        tabs = st.tabs(["Search", "Temporal Search", "Ingestion"])
        with tabs[0]:
            _tab_search()
        with tabs[1]:
            _tab_temporal_search()
        with tabs[2]:
            _tab_ingestion()


if __name__ == "__main__":
    # Only run the Streamlit app when a Streamlit runtime exists.
    # This allows `runpy.run_path(..., run_name="__main__")` smoke-checks to import safely.
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx  # type: ignore
    except Exception:
        get_script_run_ctx = None

    ctx = None
    if get_script_run_ctx:
        try:
            ctx = get_script_run_ctx()
        except Exception:
            ctx = None

    if ctx is not None:
        st.set_page_config(page_title="S3 Vectors – Streamlit", layout="wide")
        main()
    else:
        # Programmatically launch Streamlit CLI when no runtime is detected (compatible with Streamlit >= 1.33)
        try:
            from streamlit.web import cli as stcli
        except Exception:
            from streamlit import cli as stcli  # fallback for older versions
        import sys, os
        script_path = os.path.abspath(__file__)
        sys.argv = ["streamlit", "run", script_path]
        raise SystemExit(stcli.main())