#!/usr/bin/env python3
"""
evaluate.py – RAGAS Evaluation Suite for the AI Financial Agent RAG System
===========================================================================
Evaluates the quality of the RAG pipeline (retrieval + generation) using the
RAGAS framework. Uses the **same Groq LLM and sentence-transformer embeddings**
already configured for the rest of this project (GROQ_API_KEY, GROQ_MODEL,
EMBED_MODEL in .env).

Five standard RAGAS metrics:
  • faithfulness         – answer grounded in retrieved context
  • answer_relevancy    – answer addresses the question
  • context_precision   – relevant chunks ranked highly
  • context_recall      – retrieved context covers the ground truth
  • answer_correctness  – semantic + factual accuracy vs. ground truth

Usage examples
--------------
  # Run all metrics with the .env model (default)
  python evaluate.py

  # Use a different Groq model for this run
  python evaluate.py --model llama-3.1-8b-instant

  # Evaluate only specific metrics on a custom CSV file
  python evaluate.py --input_file eval_data.csv --metrics faithfulness answer_relevancy

  # Full run, custom output directory, skip charts
  python evaluate.py --input_file eval_data.json --output_dir results/ --no_viz

  # Export the built-in sample dataset so you can edit it
  python evaluate.py --save_sample

Input file format
-----------------
  question    : str   – the user question
  answer      : str   – the RAG-generated answer
  contexts    : list  – list of retrieved text chunks  (JSON-string in CSV)
  ground_truth: str   – reference / ideal answer
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import statistics
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Bootstrap – project root on sys.path so backend imports work
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

load_dotenv(_HERE / ".env")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s – %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("evaluate")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ALL_METRICS = [
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
    "answer_correctness",
]

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
TOP_N = 5  # rows shown in best / worst tables

# ---------------------------------------------------------------------------
# Defaults pulled from the project .env (same keys as config.py)
# ---------------------------------------------------------------------------
DEFAULT_GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
DEFAULT_EMBED_MODEL = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")

# ---------------------------------------------------------------------------
# Built-in sample dataset (8 realistic financial Q&A rows)
# ---------------------------------------------------------------------------
SAMPLE_DATA: list[dict[str, Any]] = [
    {
        "question": "What was Apple's total revenue in fiscal year 2023?",
        "answer": (
            "Apple reported total net sales of $383.3 billion for fiscal year 2023, "
            "a decline of approximately 2.8% compared to the $394.3 billion in FY2022."
        ),
        "contexts": [
            (
                "Apple Inc. Annual Report FY2023: Net sales were $383.3 billion, "
                "compared to $394.3 billion in FY2022, a decline of 2.8%."
            ),
            (
                "Revenue by segment: iPhone $200.6B, Mac $29.4B, iPad $28.3B, "
                "Wearables/Home/Accessories $39.8B, Services $85.2B."
            ),
            (
                "Apple's gross margin improved to 44.1% in FY2023 vs 43.3% in FY2022, "
                "driven by higher-margin Services mix."
            ),
        ],
        "ground_truth": (
            "Apple's total revenue for FY2023 was $383.3 billion, a 2.8% decrease "
            "from $394.3 billion in FY2022."
        ),
    },
    {
        "question": "What are the primary risk factors mentioned in Tesla's 10-K?",
        "answer": (
            "Tesla's 10-K highlights: intense EV competition, supply chain disruptions "
            "(especially semiconductors), regulatory uncertainty around autonomous driving, "
            "new factory ramp execution risk, and reliance on Elon Musk as a key person."
        ),
        "contexts": [
            (
                "Risk Factors – Competition: We face significant competition from established "
                "automakers and new EV entrants with greater financial resources."
            ),
            (
                "Risk Factors – Supply Chain: Our operations depend on a complex global supply chain; "
                "semiconductor shortages could materially impact production volumes."
            ),
            (
                "Risk Factors – Key Personnel: We depend heavily on Elon Musk. "
                "Loss of his services could disrupt our operations."
            ),
        ],
        "ground_truth": (
            "Tesla's primary 10-K risks: EV competition, semiconductor supply chain, "
            "autonomous vehicle regulation, manufacturing scale-up, and key-person dependency on Elon Musk."
        ),
    },
    {
        "question": "How did Microsoft's cloud revenue grow in Q4 FY2023?",
        "answer": (
            "Microsoft's Intelligent Cloud segment grew 15% YoY to $24.3 billion in Q4 FY2023. "
            "Azure and other cloud services grew 26% in constant currency."
        ),
        "contexts": [
            (
                "Q4 FY2023 Earnings: Intelligent Cloud revenue was $24.3 billion, up 15% YoY "
                "(16% in constant currency)."
            ),
            (
                "Azure and other cloud services grew 26% in constant currency, driven by AI "
                "services and enterprise cloud adoption."
            ),
        ],
        "ground_truth": (
            "Microsoft's Intelligent Cloud grew 15% YoY to $24.3B in Q4 FY2023; "
            "Azure grew 26% in constant currency."
        ),
    },
    {
        "question": "What is Amazon's current debt-to-equity ratio?",
        "answer": (
            "Amazon's debt-to-equity ratio is approximately 0.75. Long-term debt is ~$140 billion "
            "against total stockholders' equity of ~$186 billion."
        ),
        "contexts": [
            (
                "Amazon Balance Sheet (2023): Total long-term debt: $140.1 billion. "
                "Total stockholders' equity: $185.9 billion."
            ),
        ],
        "ground_truth": (
            "Amazon's debt-to-equity ratio is ~0.75, with long-term debt of ~$140B "
            "and stockholders' equity of ~$186B."
        ),
    },
    {
        "question": "What dividend did Johnson & Johnson pay in 2023?",
        "answer": (
            "Johnson & Johnson raised its quarterly dividend to $1.19 per share in 2023, "
            "an annualised rate of $4.76 – the 61st consecutive year of increases."
        ),
        "contexts": [
            (
                "In April 2023, JNJ increased its quarterly dividend by 5.3% to $1.19 per share, "
                "marking the 61st consecutive year of dividend increases."
            ),
            "JNJ's annual dividend totalled $4.76 per share in 2023.",
        ],
        "ground_truth": (
            "JNJ paid $1.19/quarter ($4.76 annualised) in 2023 — its 61st consecutive annual dividend increase."
        ),
    },
    {
        "question": "What are the main revenue segments for Alphabet (Google)?",
        "answer": (
            "Alphabet's three segments: Google Services (~$272B — Search, YouTube, Network, Subscriptions), "
            "Google Cloud (~$33B), and Other Bets (~$1.5B)."
        ),
        "contexts": [
            (
                "Alphabet 2023 Annual Report: Google Services $272.5B; Google Cloud $33.1B; "
                "Other Bets $1.5B."
            ),
            (
                "Google Services breakdown: Search & other $175.0B, YouTube ads $31.5B, "
                "Network $31.3B, Subscriptions/platforms/devices $34.7B."
            ),
        ],
        "ground_truth": (
            "Alphabet's segments: Google Services (~$272.5B), Google Cloud (~$33.1B), Other Bets (~$1.5B)."
        ),
    },
    {
        "question": "What is the current P/E ratio of the S&P 500?",
        "answer": (
            "Based on available data, the S&P 500 trailing P/E ratio was approximately 25x "
            "as of Q4 2023, above the long-run historical average of ~16x."
        ),
        "contexts": [
            (
                "Market Valuation Note (Q4 2023): S&P 500 trailing 12-month P/E ratio stood at "
                "approximately 24.5–25.0x, above the long-run historical average of ~16x."
            ),
        ],
        "ground_truth": (
            "The S&P 500 trailing P/E ratio was ~24.5–25x in Q4 2023, above the ~16x historical average."
        ),
    },
    {
        "question": "How does Warren Buffett's philosophy shape Berkshire Hathaway's portfolio?",
        "answer": (
            "Buffett's value investing approach — buying quality businesses with durable moats at fair prices — "
            "creates a concentrated portfolio. Top holdings: Apple ~50%, Bank of America 9.3%, "
            "American Express 7.5%, Coca-Cola 7.0%."
        ),
        "contexts": [
            (
                "Berkshire 2023 Shareholder Letter: Buffett reiterated preference for businesses with "
                "durable competitive advantages, consistent earnings, and capable management."
            ),
            (
                "Top Berkshire Equity Holdings Q4 2023: Apple 50.2%, Bank of America 9.3%, "
                "American Express 7.5%, Coca-Cola 7.0%, Chevron 4.5%."
            ),
        ],
        "ground_truth": (
            "Buffett's value-investing results in a concentrated portfolio dominated by Apple (~50%), "
            "Bank of America, American Express, and Coca-Cola."
        ),
    },
]


# ===========================================================================
# LLM & Embeddings – Groq + HuggingFace (mirrors the project's own stack)
# ===========================================================================

def _build_ragas_llm(groq_model: str):
    """
    Return a LangChain ChatGroq model wrapped for RAGAS.

    Requires:
      pip install langchain-groq
      GROQ_API_KEY in .env
    """
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY is not set.  Add it to your .env file:\n"
            "  GROQ_API_KEY=gsk_..."
        )

    try:
        from langchain_groq import ChatGroq
    except ImportError:
        raise ImportError(
            "langchain-groq is not installed.\n"
            "Run:  pip install langchain-groq"
        )

    logger.info("LLM judge : ChatGroq / %s", groq_model)
    return ChatGroq(
        model=groq_model,
        groq_api_key=api_key,
        temperature=0,
        max_tokens=4096,
    )


def _build_ragas_embeddings(embed_model: str):
    """
    Return HuggingFace SentenceTransformer embeddings — the same model the
    project's retriever already downloads (EMBED_MODEL in .env).

    Requires:
      pip install langchain-community sentence-transformers
      (both are already in requirements.txt)
    """
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
    except ImportError:
        raise ImportError(
            "langchain-community is not installed.\n"
            "Run:  pip install langchain-community"
        )

    logger.info("Embeddings: HuggingFace / %s", embed_model)
    return HuggingFaceEmbeddings(model_name=embed_model)


# ===========================================================================
# Data loading
# ===========================================================================

def load_evaluation_data(input_file: str | None) -> list[dict[str, Any]]:
    """
    Load evaluation rows from a CSV or JSON file.

    Expected columns / keys: question, answer, contexts, ground_truth
    In CSV, 'contexts' must be a JSON-encoded list of strings.
    If input_file is None the built-in SAMPLE_DATA is returned.
    """
    if not input_file:
        logger.info(
            "No --input_file given – using built-in sample data (%d rows).",
            len(SAMPLE_DATA),
        )
        return SAMPLE_DATA

    path = Path(input_file)
    if not path.exists():
        raise FileNotFoundError(f"Evaluation file not found: {input_file}")

    suffix = path.suffix.lower()
    logger.info("Loading evaluation data from: %s", path)

    if suffix == ".json":
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        rows: list[dict] = raw if isinstance(raw, list) else raw.get("data", [])

    elif suffix == ".csv":
        df = pd.read_csv(path)
        rows = df.to_dict(orient="records")
        for row in rows:
            if isinstance(row.get("contexts"), str):
                try:
                    row["contexts"] = json.loads(row["contexts"])
                except json.JSONDecodeError:
                    row["contexts"] = [row["contexts"]]
    else:
        raise ValueError(f"Unsupported file format '{suffix}'. Use .csv or .json")

    required = {"question", "answer", "contexts", "ground_truth"}
    for i, row in enumerate(rows):
        missing = required - set(row.keys())
        if missing:
            raise ValueError(f"Row {i} is missing required keys: {missing}")

    logger.info("Loaded %d evaluation rows.", len(rows))
    return rows


def save_sample_data(output_path: str = "sample_eval_data.json") -> None:
    """Write the built-in sample dataset to a JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(SAMPLE_DATA, f, indent=2, ensure_ascii=False)
    logger.info("Sample data saved to: %s", output_path)


# ===========================================================================
# RAGAS metric objects
# ===========================================================================

def get_metric_objects(metric_names: list[str]) -> list:
    """Import and return RAGAS metric instances by name."""
    try:
        from ragas.metrics import (
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
            answer_correctness,
        )
    except ImportError:
        raise ImportError(
            "ragas is not installed.\n"
            "Run:  pip install ragas"
        )

    metric_map = {
        "faithfulness": faithfulness,
        "answer_relevancy": answer_relevancy,
        "context_precision": context_precision,
        "context_recall": context_recall,
        "answer_correctness": answer_correctness,
    }

    selected = []
    for name in metric_names:
        if name not in metric_map:
            logger.warning("Unknown metric '%s' – skipping.", name)
        else:
            selected.append(metric_map[name])

    if not selected:
        raise ValueError("No valid metrics selected.")
    return selected


# ===========================================================================
# Build RAGAS Dataset
# ===========================================================================

def build_ragas_dataset(rows: list[dict[str, Any]]):
    """Convert evaluation row dicts to a RAGAS EvaluationDataset (or HF Dataset)."""
    # Try ragas >= 0.2 new API first
    try:
        from ragas import EvaluationDataset, SingleTurnSample

        samples = [
            SingleTurnSample(
                user_input=r["question"],
                response=r["answer"],
                retrieved_contexts=r["contexts"],
                reference=r["ground_truth"],
            )
            for r in rows
        ]
        return EvaluationDataset(samples=samples)

    except ImportError:
        pass  # fall through to legacy path

    # Legacy ragas (< 0.2) uses a HuggingFace Dataset directly
    try:
        from datasets import Dataset as HFDataset  # type: ignore

        return HFDataset.from_dict(
            {
                "question": [r["question"] for r in rows],
                "answer": [r["answer"] for r in rows],
                "contexts": [r["contexts"] for r in rows],
                "ground_truth": [r["ground_truth"] for r in rows],
            }
        )
    except ImportError:
        raise ImportError(
            "Could not import ragas EvaluationDataset or HuggingFace datasets.\n"
            "Run:  pip install ragas datasets"
        )


# ===========================================================================
# Core evaluation pipeline
# ===========================================================================

def run_evaluation(
    rows: list[dict[str, Any]],
    metric_names: list[str],
    groq_model: str,
    embed_model: str,
    batch_size: int = 4,
) -> pd.DataFrame:
    """
    Run RAGAS evaluation and return a per-row results DataFrame.

    Parameters
    ----------
    rows         : evaluation data
    metric_names : RAGAS metric names to compute
    groq_model   : Groq model identifier (e.g. 'llama-3.3-70b-versatile')
    embed_model  : HuggingFace model name (e.g. 'all-MiniLM-L6-v2')
    batch_size   : samples per RAGAS call (keeps API payloads manageable)
    """
    logger.info("Initialising Groq LLM and HuggingFace embeddings …")
    lc_llm = _build_ragas_llm(groq_model)
    lc_emb = _build_ragas_embeddings(embed_model)

    logger.info("Loading RAGAS metric objects: %s", metric_names)
    metrics = get_metric_objects(metric_names)

    # Inject models into each metric (ragas >= 0.2 wrapper approach)
    try:
        from ragas.llms import LangchainLLMWrapper
        from ragas.embeddings import LangchainEmbeddingsWrapper

        wrapped_llm = LangchainLLMWrapper(lc_llm)
        wrapped_emb = LangchainEmbeddingsWrapper(lc_emb)

        for m in metrics:
            if hasattr(m, "llm"):
                m.llm = wrapped_llm
            if hasattr(m, "embeddings"):
                m.embeddings = wrapped_emb

        logger.info("RAGAS >= 0.2 — LLM and embeddings injected into metrics.")
    except ImportError:
        # Older ragas passes models at evaluate() call time
        logger.debug("Pre-0.2 ragas API detected — will pass models at evaluate() time.")
        wrapped_llm = lc_llm  # type: ignore
        wrapped_emb = lc_emb  # type: ignore

    # Batch loop
    num_batches = (len(rows) + batch_size - 1) // batch_size
    all_results: list[pd.DataFrame] = []

    for batch_idx in range(num_batches):
        batch = rows[batch_idx * batch_size : (batch_idx + 1) * batch_size]
        logger.info(
            "Evaluating batch %d / %d  (%d samples) …",
            batch_idx + 1,
            num_batches,
            len(batch),
        )

        dataset = build_ragas_dataset(batch)

        try:
            from ragas import evaluate

            # ragas >= 0.2
            try:
                result = evaluate(dataset=dataset, metrics=metrics)
            except TypeError:
                # Legacy: pass llm & embeddings explicitly
                result = evaluate(
                    dataset,
                    metrics=metrics,
                    llm=wrapped_llm,
                    embeddings=wrapped_emb,
                )

            try:
                result_df = result.to_pandas()
            except Exception:
                result_df = pd.DataFrame(result.scores)

            # Attach original text columns
            result_df["question"] = [r["question"] for r in batch]
            result_df["answer"] = [r["answer"] for r in batch]
            result_df["ground_truth"] = [r["ground_truth"] for r in batch]

            all_results.append(result_df)

        except Exception as exc:
            logger.error("Batch %d failed: %s", batch_idx + 1, exc)
            logger.debug(traceback.format_exc())
            # Placeholder NaN row so we don't lose track of samples
            placeholder = pd.DataFrame(
                [
                    {
                        "question": r["question"],
                        "answer": r["answer"],
                        "ground_truth": r["ground_truth"],
                        **{m: float("nan") for m in metric_names},
                    }
                    for r in batch
                ]
            )
            all_results.append(placeholder)

    if not all_results:
        raise RuntimeError("All evaluation batches failed. Check the logs above.")

    final_df = pd.concat(all_results, ignore_index=True)

    # Ensure every requested metric column exists
    for m in metric_names:
        if m not in final_df.columns:
            final_df[m] = float("nan")

    return final_df


# ===========================================================================
# Statistics
# ===========================================================================

def compute_aggregate_stats(df: pd.DataFrame, metric_names: list[str]) -> dict[str, dict]:
    """Mean, median, std, min, max for each metric column."""
    stats: dict[str, dict] = {}
    for metric in metric_names:
        col = df[metric].dropna()
        if col.empty:
            stats[metric] = dict(mean=None, median=None, std=None, min=None, max=None)
        else:
            stats[metric] = dict(
                mean=round(float(col.mean()), 4),
                median=round(float(col.median()), 4),
                std=round(float(col.std()), 4),
                min=round(float(col.min()), 4),
                max=round(float(col.max()), 4),
            )
    return stats


def compute_overall_score(df: pd.DataFrame, metric_names: list[str]) -> float:
    """Unweighted average across all metrics and all rows."""
    values = [df[m].dropna().mean() for m in metric_names if m in df.columns and not df[m].dropna().empty]
    return round(statistics.mean(values), 4) if values else 0.0


def get_best_worst(
    df: pd.DataFrame, metric_names: list[str], n: int = TOP_N
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Top-n and bottom-n rows ranked by average metric score."""
    valid = [m for m in metric_names if m in df.columns]
    df = df.copy()
    df["_avg"] = df[valid].mean(axis=1)
    best = df.nlargest(n, "_avg").drop(columns=["_avg"])
    worst = df.nsmallest(n, "_avg").drop(columns=["_avg"])
    return best, worst


# ===========================================================================
# Output: CSV / JSON / text report
# ===========================================================================

def save_results(
    df: pd.DataFrame,
    stats: dict[str, dict],
    overall_score: float,
    output_dir: str,
    metric_names: list[str],
    groq_model: str,
    embed_model: str,
) -> tuple[Path, Path, Path]:
    """
    Save:
      • {prefix}_results.csv      – full per-row results
      • {prefix}_stats.json       – aggregate statistics
      • {prefix}_report.txt       – human-readable console report
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    prefix = f"ragas_eval_{TIMESTAMP}"

    # 1. Results CSV
    csv_path = out / f"{prefix}_results.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8")
    logger.info("Full results  → %s", csv_path)

    # 2. Stats JSON
    json_payload = {
        "timestamp": TIMESTAMP,
        "groq_model": groq_model,
        "embed_model": embed_model,
        "num_samples": len(df),
        "metrics_evaluated": metric_names,
        "overall_score": overall_score,
        "per_metric_stats": stats,
    }
    json_path = out / f"{prefix}_stats.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_payload, f, indent=2, ensure_ascii=False)
    logger.info("Aggregate stats → %s", json_path)

    # 3. Summary report
    best, worst = get_best_worst(df, metric_names)
    lines: list[str] = []

    lines.append("=" * 70)
    lines.append("  RAGAS EVALUATION REPORT – AI Financial Agent")
    lines.append("=" * 70)
    lines.append(f"  Timestamp    : {TIMESTAMP}")
    lines.append(f"  Groq Model   : {groq_model}")
    lines.append(f"  Embed Model  : {embed_model}")
    lines.append(f"  Samples      : {len(df)}")
    lines.append(f"  Metrics      : {', '.join(metric_names)}")
    lines.append(f"  Overall Score: {overall_score:.4f}")
    lines.append("")
    lines.append("─" * 70)
    lines.append("  PER-METRIC STATISTICS")
    lines.append("─" * 70)
    lines.append(f"{'Metric':<25} {'Mean':>7} {'Median':>8} {'Std':>7} {'Min':>7} {'Max':>7}")
    lines.append("─" * 70)
    for metric, s in stats.items():
        if s["mean"] is None:
            lines.append(f"{metric:<25} {'N/A':>7}")
        else:
            lines.append(
                f"{metric:<25} {s['mean']:>7.4f} {s['median']:>8.4f} "
                f"{s['std']:>7.4f} {s['min']:>7.4f} {s['max']:>7.4f}"
            )

    lines.append("")
    lines.append("─" * 70)
    lines.append(f"  TOP {TOP_N} BEST PERFORMING QUERIES")
    lines.append("─" * 70)
    for rank, (_, row) in enumerate(best.iterrows(), 1):
        q = str(row.get("question", ""))[:80]
        scores = "  ".join(
            f"{m}: {row[m]:.3f}" for m in metric_names if m in row and pd.notna(row[m])
        )
        lines.append(f"  {rank}. {q}")
        lines.append(f"     {scores}")

    lines.append("")
    lines.append("─" * 70)
    lines.append(f"  TOP {TOP_N} WORST PERFORMING QUERIES")
    lines.append("─" * 70)
    for rank, (_, row) in enumerate(worst.iterrows(), 1):
        q = str(row.get("question", ""))[:80]
        scores = "  ".join(
            f"{m}: {row[m]:.3f}" for m in metric_names if m in row and pd.notna(row[m])
        )
        lines.append(f"  {rank}. {q}")
        lines.append(f"     {scores}")

    lines.append("")
    lines.append("=" * 70)
    lines.append("  METRIC INTERPRETATION GUIDE")
    lines.append("─" * 70)
    guide = [
        ("faithfulness",      "% of answer claims supported by context  [0=hallucinated, 1=fully grounded]"),
        ("answer_relevancy",  "Answer addresses the question             [0=irrelevant, 1=fully relevant]"),
        ("context_precision", "Relevant chunks ranked at top of retrieval [0=poor rank, 1=perfect rank]"),
        ("context_recall",    "Context covers the ground truth           [0=missing info, 1=complete]"),
        ("answer_correctness","Semantic/factual accuracy vs. ground truth [0=wrong, 1=correct]"),
    ]
    for name, desc in guide:
        if name in metric_names:
            lines.append(f"  {name:<25} {desc}")
    lines.append("=" * 70)

    report_text = "\n".join(lines)
    report_path = out / f"{prefix}_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)
    logger.info("Summary report  → %s", report_path)
    print("\n" + report_text + "\n")

    return csv_path, json_path, report_path


# ===========================================================================
# Optional visualizations
# ===========================================================================

def create_visualizations(
    df: pd.DataFrame,
    stats: dict[str, dict],
    metric_names: list[str],
    output_dir: str,
) -> list[Path]:
    """Generate a bar chart and distribution histograms as PNG files."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
    except ImportError:
        logger.warning(
            "matplotlib not installed – skipping charts.  "
            "Install with:  pip install matplotlib"
        )
        return []

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    prefix = f"ragas_eval_{TIMESTAMP}"
    saved: list[Path] = []

    valid = [m for m in metric_names if stats.get(m, {}).get("mean") is not None]
    if not valid:
        logger.warning("No valid metric data for visualization.")
        return []

    # ── 1. Mean scores bar chart ──────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 5))
    means = [stats[m]["mean"] for m in valid]
    colors = [
        "#4FC3F7" if v >= 0.8 else "#FFD54F" if v >= 0.6 else "#EF5350"
        for v in means
    ]
    bars = ax.bar(valid, means, color=colors, edgecolor="white", linewidth=1.2)
    ax.set_ylim(0, 1.1)
    ax.set_ylabel("Score (0 – 1)", fontsize=12)
    ax.set_title(
        f"RAGAS Evaluation – Mean Metric Scores\n({DEFAULT_GROQ_MODEL})",
        fontsize=13,
        fontweight="bold",
    )
    ax.axhline(0.8, color="#4FC3F7", linestyle="--", linewidth=0.9, alpha=0.7)
    ax.axhline(0.6, color="#FFD54F", linestyle="--", linewidth=0.9, alpha=0.7)
    ax.tick_params(axis="x", rotation=15)
    for bar, val in zip(bars, means):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.015,
            f"{val:.3f}",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )
    patches = [
        mpatches.Patch(color="#4FC3F7", label="≥ 0.8 Good"),
        mpatches.Patch(color="#FFD54F", label="0.6–0.8 Fair"),
        mpatches.Patch(color="#EF5350", label="< 0.6 Poor"),
    ]
    ax.legend(handles=patches, loc="upper right", fontsize=9)
    fig.tight_layout()
    bar_path = out / f"{prefix}_bar_chart.png"
    fig.savefig(bar_path, dpi=150)
    plt.close(fig)
    saved.append(bar_path)
    logger.info("Bar chart saved → %s", bar_path)

    # ── 2. Score distribution grid ────────────────────────────────────────
    n_cols = min(len(valid), 3)
    n_rows = (len(valid) + n_cols - 1) // n_cols
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 4 * n_rows))
    flat = axes.flatten() if hasattr(axes, "flatten") else [axes]

    for idx, metric in enumerate(valid):
        ax = flat[idx]
        col = df[metric].dropna()
        bins = min(10, max(3, len(col) // 2))
        ax.hist(col, bins=bins, color="#4FC3F7", edgecolor="white")
        ax.axvline(float(col.mean()), color="#EF5350", linestyle="--", linewidth=1.5,
                   label=f"Mean {col.mean():.3f}")
        ax.set_title(metric, fontsize=11, fontweight="bold")
        ax.set_xlabel("Score")
        ax.set_ylabel("Frequency")
        ax.set_xlim(0, 1)
        ax.legend(fontsize=8)

    for idx in range(len(valid), len(flat)):
        flat[idx].set_visible(False)

    fig.suptitle("RAGAS Score Distributions", fontsize=14, fontweight="bold", y=1.01)
    fig.tight_layout()
    dist_path = out / f"{prefix}_distributions.png"
    fig.savefig(dist_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    saved.append(dist_path)
    logger.info("Distribution plot → %s", dist_path)

    return saved


# ===========================================================================
# CLI
# ===========================================================================

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="evaluate.py",
        description=(
            "RAGAS evaluation suite for the AI Financial Agent RAG system.\n"
            "Uses the Groq LLM and sentence-transformer embeddings already\n"
            "configured in your .env (GROQ_API_KEY, GROQ_MODEL, EMBED_MODEL)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python evaluate.py\n"
            "  python evaluate.py --input_file eval_data.csv\n"
            "  python evaluate.py --metrics faithfulness context_recall\n"
            "  python evaluate.py --model llama-3.1-8b-instant\n"
            "  python evaluate.py --no_viz --output_dir ./results\n"
            "  python evaluate.py --save_sample\n"
        ),
    )
    parser.add_argument(
        "--input_file",
        type=str,
        default=None,
        help=(
            "Path to evaluation dataset (.csv or .json). "
            "If omitted, the built-in 8-row financial sample is used."
        ),
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="evaluation_results",
        help="Directory for output files (default: evaluation_results/).",
    )
    parser.add_argument(
        "--metrics",
        nargs="+",
        choices=ALL_METRICS,
        default=ALL_METRICS,
        metavar="METRIC",
        help=(
            f"Metrics to compute. Choices: {', '.join(ALL_METRICS)}. "
            "Default: all."
        ),
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_GROQ_MODEL,
        help=(
            "Groq model identifier for the RAGAS LLM judge. "
            "Reads GROQ_MODEL from .env by default. "
            f"(default: {DEFAULT_GROQ_MODEL})"
        ),
    )
    parser.add_argument(
        "--embed_model",
        type=str,
        default=DEFAULT_EMBED_MODEL,
        help=(
            "HuggingFace embedding model name. "
            "Reads EMBED_MODEL from .env by default. "
            f"(default: {DEFAULT_EMBED_MODEL})"
        ),
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=4,
        help="Samples per RAGAS evaluation call (default: 4).",
    )
    parser.add_argument(
        "--no_viz",
        action="store_true",
        default=False,
        help="Skip PNG chart generation.",
    )
    parser.add_argument(
        "--save_sample",
        action="store_true",
        default=False,
        help="Write built-in sample data to sample_eval_data.json and exit.",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="Enable DEBUG-level logging.",
    )
    return parser


# ===========================================================================
# Entry point
# ===========================================================================

def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.save_sample:
        save_sample_data()
        sys.exit(0)

    logger.info("=" * 60)
    logger.info("AI Financial Agent – RAGAS Evaluation Suite")
    logger.info("=" * 60)
    logger.info("Groq Model   : %s", args.model)
    logger.info("Embed Model  : %s", args.embed_model)
    logger.info("Metrics      : %s", ", ".join(args.metrics))
    logger.info("Output dir   : %s", args.output_dir)
    logger.info("Batch size   : %d", args.batch_size)
    logger.info(
        "Input file   : %s",
        args.input_file if args.input_file else "(built-in sample data)",
    )

    # Load data
    try:
        rows = load_evaluation_data(args.input_file)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Failed to load data: %s", exc)
        sys.exit(1)

    if not rows:
        logger.error("Dataset is empty. Aborting.")
        sys.exit(1)

    # Run evaluation
    logger.info("Starting RAGAS evaluation on %d samples …", len(rows))
    try:
        results_df = run_evaluation(
            rows=rows,
            metric_names=args.metrics,
            groq_model=args.model,
            embed_model=args.embed_model,
            batch_size=args.batch_size,
        )
    except (ImportError, EnvironmentError) as exc:
        logger.error("%s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.error("Evaluation failed: %s", exc)
        logger.debug(traceback.format_exc())
        sys.exit(1)

    # Post-process
    stats = compute_aggregate_stats(results_df, args.metrics)
    overall = compute_overall_score(results_df, args.metrics)

    # Save outputs
    csv_path, json_path, report_path = save_results(
        df=results_df,
        stats=stats,
        overall_score=overall,
        output_dir=args.output_dir,
        metric_names=args.metrics,
        groq_model=args.model,
        embed_model=args.embed_model,
    )

    # Visualizations
    if not args.no_viz:
        png_paths = create_visualizations(
            df=results_df,
            stats=stats,
            metric_names=args.metrics,
            output_dir=args.output_dir,
        )
        if png_paths:
            logger.info("Charts: %s", ", ".join(str(p) for p in png_paths))

    # Final summary
    logger.info("Done.")
    logger.info("  Results CSV  : %s", csv_path)
    logger.info("  Stats JSON   : %s", json_path)
    logger.info("  Report TXT   : %s", report_path)
    logger.info("  Overall Score: %.4f", overall)


if __name__ == "__main__":
    main()
