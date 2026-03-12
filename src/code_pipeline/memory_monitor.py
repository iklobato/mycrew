"""Memory monitoring and optimization utilities for the code pipeline."""

import gc
import gzip
import logging
import os
import pickle
import psutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


def get_memory_usage() -> dict[str, float]:
    """Get current memory usage statistics."""
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()

    return {
        "rss_mb": mem_info.rss / 1024 / 1024,  # Resident Set Size
        "vms_mb": mem_info.vms / 1024 / 1024,  # Virtual Memory Size
        "percent": process.memory_percent(),
        "available_mb": psutil.virtual_memory().available / 1024 / 1024,
        "total_mb": psutil.virtual_memory().total / 1024 / 1024,
    }


def log_memory_usage(prefix: str = "") -> None:
    """Log current memory usage."""
    try:
        mem = get_memory_usage()
        logger.info(
            "%sMemory: RSS=%.1fMB, VMS=%.1fMB, %.1f%%, Available=%.1fMB/%.1fMB",
            f"{prefix} " if prefix else "",
            mem["rss_mb"],
            mem["vms_mb"],
            mem["percent"],
            mem["available_mb"],
            mem["total_mb"],
        )
    except Exception as e:
        logger.debug("Failed to get memory usage: %s", e)


def force_garbage_collection(threshold_mb: Optional[float] = None) -> None:
    """Aggressive garbage collection with multiple cycles to free more memory."""
    try:
        mem_before = get_memory_usage()

        # Aggressive collection: multiple cycles to catch cyclic references
        total_collected = 0
        cycles_completed = 0
        for cycle in range(3):  # Three collection cycles
            collected = gc.collect(
                2 if cycle > 0 else 0
            )  # Generation 2 on subsequent cycles
            total_collected += collected
            cycles_completed = cycle + 1

            if cycle == 0:
                # First cycle: collect all generations
                logger.debug(
                    "GC cycle %d: collected %d objects", cycles_completed, collected
                )
            else:
                # Subsequent cycles: collect older generations
                logger.debug(
                    "GC cycle %d (generation %d): collected %d objects",
                    cycles_completed,
                    2,
                    collected,
                )

            if collected == 0 and cycle > 0:
                # No more objects to collect
                break

        mem_after = get_memory_usage()
        freed_mb = mem_before["rss_mb"] - mem_after["rss_mb"]

        if freed_mb > 0.1:  # Only log if significant memory was freed
            logger.info(
                "GC collected %d objects over %d cycles, freed %.1fMB memory (RSS: %.1fMB -> %.1fMB)",
                total_collected,
                cycles_completed,
                freed_mb,
                mem_before["rss_mb"],
                mem_after["rss_mb"],
            )
        elif (
            total_collected > 100
        ):  # Log even if memory not freed but objects collected
            logger.debug(
                "GC collected %d objects (memory unchanged: %.1fMB RSS)",
                total_collected,
                mem_after["rss_mb"],
            )

        # If memory usage is above threshold, log warning
        if threshold_mb and mem_after["rss_mb"] > threshold_mb:
            logger.warning(
                "High memory usage: %.1fMB RSS (threshold: %.1fMB)",
                mem_after["rss_mb"],
                threshold_mb,
            )

    except Exception as e:
        logger.debug("Failed to force garbage collection: %s", e)


class MemoryGuard:
    """Context manager to monitor and limit memory usage."""

    def __init__(self, name: str, warning_threshold_mb: float = 500.0):
        self.name = name
        self.warning_threshold_mb = warning_threshold_mb
        self.mem_before: Optional[dict[str, float]] = None

    def __enter__(self) -> "MemoryGuard":
        self.mem_before = get_memory_usage()
        logger.info(
            "┌─[ MEMORY GUARD: %s ]─ Start: RSS=%.1fMB",
            self.name,
            self.mem_before["rss_mb"],
        )
        return self

    def __exit__(
        self, exc_type: Any | None, exc_val: Any | None, exc_tb: Any | None
    ) -> None:
        if self.mem_before:
            mem_after = get_memory_usage()
            delta_mb = mem_after["rss_mb"] - self.mem_before["rss_mb"]

            logger.info(
                "└─[ MEMORY GUARD: %s ]─ End: RSS=%.1fMB (Δ%.1fMB)",
                self.name,
                mem_after["rss_mb"],
                delta_mb,
            )

            if mem_after["rss_mb"] > self.warning_threshold_mb:
                logger.warning(
                    "High memory after %s: %.1fMB RSS",
                    self.name,
                    mem_after["rss_mb"],
                )

            # Aggressive GC forcing: always force GC after memory-intensive operations
            # and be more sensitive to memory increases
            if delta_mb > 20.0:  # Reduced from 50MB to 20MB
                logger.info(
                    "Memory increased by %.1fMB, forcing aggressive garbage collection",
                    delta_mb,
                )
                force_garbage_collection()

                # Force another GC cycle after a short delay to catch cyclic references
                import time

                time.sleep(0.1)  # Short delay
                gc.collect()  # Second collection pass

                # Log memory after second GC
                mem_final = get_memory_usage()
                final_delta = mem_final["rss_mb"] - mem_after["rss_mb"]
                if final_delta < -0.1:  # If we freed more memory
                    logger.info(
                        "Second GC pass freed additional %.1fMB memory",
                        -final_delta,
                    )
            elif mem_after["rss_mb"] > self.warning_threshold_mb * 0.7:
                # Force GC if we're approaching warning threshold
                logger.info(
                    "Approaching memory threshold (%.1fMB), forcing preventive GC",
                    mem_after["rss_mb"],
                )
                force_garbage_collection()


def optimize_memory_settings() -> None:
    """Optimize Python memory settings for better performance."""
    # Increase GC thresholds for better performance (fewer collections)
    gc.set_threshold(700, 10, 10)

    # Disable debug features in production
    if not sys.flags.debug:
        gc.disable()
        gc.enable()  # Re-enable with optimized settings

    logger.info("Memory settings optimized: GC thresholds increased")


# ============================================================================
# LLM CONTEXT MANAGEMENT
# ============================================================================


def estimate_context_size(text: str, tokens_per_char: float = 0.25) -> int:
    """Estimate token count for text using average token-to-character ratio.

    Args:
        text: Text to estimate token count for
        tokens_per_char: Average tokens per character (default 0.25 based on typical LLM tokenization)

    Returns:
        Estimated token count
    """
    if not text:
        return 0

    # Simple estimation: characters * average tokens per character
    # This is a rough estimate but sufficient for memory optimization decisions
    return int(len(text) * tokens_per_char)


def calculate_optimal_max_tokens(
    context_text: str,
    max_context_tokens: int = 8000,
    min_output_tokens: int = 512,
    safety_margin: float = 0.2,
) -> int:
    """Calculate optimal max_tokens based on context size with safety margin.

    Args:
        context_text: The context/prompt text being sent to LLM
        max_context_tokens: Maximum context window size for the model
        min_output_tokens: Minimum tokens to reserve for output
        safety_margin: Safety margin to reserve (0.2 = 20% of remaining tokens)

    Returns:
        Optimal max_tokens setting
    """
    estimated_context_tokens = estimate_context_size(context_text)

    # Calculate available tokens for output
    available_for_output = max_context_tokens - estimated_context_tokens

    # Apply safety margin
    safe_available = int(available_for_output * (1.0 - safety_margin))

    # Ensure we have at least minimum output tokens
    if safe_available < min_output_tokens:
        if available_for_output < min_output_tokens:
            # Not enough tokens even without safety margin
            logger.warning(
                "Context too large: %d tokens estimated, only %d tokens available for output (min: %d)",
                estimated_context_tokens,
                available_for_output,
                min_output_tokens,
            )
            return min_output_tokens  # Use minimum anyway, LLM will truncate
        # Use available tokens without safety margin if we can meet minimum
        return max(min_output_tokens, available_for_output)

    # Cap at reasonable maximum to avoid waste
    max_reasonable = 4096  # Even with large context, rarely need more than 4K output
    return min(safe_available, max_reasonable)


def get_stage_max_tokens(
    stage_name: str, context_text: str, base_max_tokens: int = 2048
) -> int:
    """Get stage-specific max_tokens with dynamic adjustment for large contexts.

    Args:
        stage_name: Pipeline stage name
        context_text: Context/prompt text for this stage
        base_max_tokens: Base max_tokens value to use as fallback

    Returns:
        Adjusted max_tokens for the stage
    """
    # Stages with typically large context inputs
    large_context_stages = {"explore", "plan", "implement", "review"}

    # Reduced max_tokens for stages with large context
    if stage_name in large_context_stages:
        # Estimate context size
        context_tokens = estimate_context_size(context_text)

        # If context is already large, reduce max_tokens aggressively
        if context_tokens > 4000:  # 4K tokens of context
            reduced = max(1024, base_max_tokens - 1024)  # Reduce by 1K
            logger.debug(
                "Large context (%d tokens) for stage %s, reducing max_tokens to %d",
                context_tokens,
                stage_name,
                reduced,
            )
            return reduced
        elif context_tokens > 2000:  # 2K tokens of context
            reduced = max(1536, base_max_tokens - 512)  # Reduce by 512
            logger.debug(
                "Moderate context (%d tokens) for stage %s, reducing max_tokens to %d",
                context_tokens,
                stage_name,
                reduced,
            )
            return reduced

    return base_max_tokens


# ============================================================================
# COMPRESSION STRATEGY
# ============================================================================


@dataclass(frozen=True)
class CompressionResult:
    """Result of compression operation."""

    compressed_data: bytes
    original_size: int
    compressed_size: int
    compression_ratio: float
    method: str


def compress_large_string(
    text: str, threshold_kb: int = 5, compression_level: int = 6
) -> CompressionResult | None:
    """Compress large strings if they exceed threshold.

    Args:
        text: Text to potentially compress
        threshold_kb: Size threshold in KB to trigger compression
        compression_level: gzip compression level (1-9)

    Returns:
        CompressionResult if compressed, None if below threshold
    """
    if not text:
        return None

    size_bytes = len(text.encode("utf-8"))
    size_kb = size_bytes / 1024

    if size_kb <= threshold_kb:
        return None

    # Compress using gzip
    compressed = gzip.compress(text.encode("utf-8"), compresslevel=compression_level)
    compressed_size = len(compressed)
    ratio = compressed_size / size_bytes if size_bytes > 0 else 0

    logger.debug(
        "Compressed string: %d KB -> %d KB (ratio: %.2f)",
        size_kb,
        compressed_size / 1024,
        ratio,
    )

    return CompressionResult(
        compressed_data=compressed,
        original_size=size_bytes,
        compressed_size=compressed_size,
        compression_ratio=ratio,
        method="gzip",
    )


def decompress_string(compressed_result: CompressionResult) -> str:
    """Decompress a compressed string."""
    if compressed_result.method == "gzip":
        return gzip.decompress(compressed_result.compressed_data).decode("utf-8")
    else:
        raise ValueError(f"Unsupported compression method: {compressed_result.method}")


class DiskBackedCache:
    """Disk-backed cache for extremely large outputs (>50KB)."""

    def __init__(self, cache_dir: str | None = None, max_size_mb: int = 100):
        self.cache_dir = (
            Path(cache_dir or tempfile.gettempdir()) / "code_pipeline_cache"
        )
        self.max_size_mb = max_size_mb
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """Create cache directory if it doesn't exist."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, key: str) -> Path:
        """Get file path for cache key."""
        # Use hash of key as filename for safety
        import hashlib

        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"

    def _cleanup_old_files(self) -> None:
        """Clean up old cache files if cache exceeds max size."""
        try:
            # Get all cache files with modification times
            cache_files = []
            total_size = 0

            for file_path in self.cache_dir.glob("*.cache"):
                if file_path.is_file():
                    size = file_path.stat().st_size
                    mtime = file_path.stat().st_mtime
                    cache_files.append((file_path, size, mtime))
                    total_size += size

            # Check if we exceed max size
            if total_size > self.max_size_mb * 1024 * 1024:
                # Sort by modification time (oldest first)
                cache_files.sort(key=lambda x: x[2])

                # Remove oldest files until under limit
                for file_path, size, _ in cache_files:
                    try:
                        file_path.unlink()
                        total_size -= size
                        logger.debug("Cleaned up old cache file: %s", file_path.name)
                    except Exception:
                        pass

                    if (
                        total_size <= self.max_size_mb * 1024 * 1024 * 0.9
                    ):  # Leave 10% buffer
                        break

        except Exception as e:
            logger.debug("Cache cleanup failed: %s", e)

    def store(self, key: str, data: Any, threshold_kb: int = 50) -> bool:
        """Store data in disk cache if it exceeds threshold.

        Args:
            key: Cache key
            data: Data to store (must be serializable)
            threshold_kb: Size threshold in KB to trigger disk storage

        Returns:
            True if stored on disk, False if kept in memory
        """
        try:
            # Serialize to estimate size
            serialized = pickle.dumps(data)
            size_kb = len(serialized) / 1024

            if size_kb <= threshold_kb:
                return False  # Keep in memory

            # Store on disk
            cache_path = self._get_cache_path(key)
            with open(cache_path, "wb") as f:
                # Compress before writing
                compressed = gzip.compress(serialized, compresslevel=6)
                f.write(compressed)

            logger.debug(
                "Stored %d KB data on disk for key: %s (compressed to %d KB)",
                size_kb,
                key,
                len(compressed) / 1024,
            )

            # Cleanup old files if needed
            self._cleanup_old_files()

            return True

        except Exception as e:
            logger.debug("Failed to store in disk cache: %s", e)
            return False

    def retrieve(self, key: str) -> Any | None:
        """Retrieve data from disk cache."""
        try:
            cache_path = self._get_cache_path(key)
            if not cache_path.exists():
                return None

            with open(cache_path, "rb") as f:
                compressed = f.read()
                serialized = gzip.decompress(compressed)
                return pickle.loads(serialized)

        except Exception as e:
            logger.debug("Failed to retrieve from disk cache: %s", e)
            return None

    def delete(self, key: str) -> None:
        """Delete data from disk cache."""
        try:
            cache_path = self._get_cache_path(key)
            if cache_path.exists():
                cache_path.unlink()
        except Exception:
            pass


# ============================================================================
# AGENT OUTPUT FILTERING
# ============================================================================


def filter_redundant_output(
    current_output: str, previous_outputs: list[str], similarity_threshold: float = 0.7
) -> str:
    """Filter redundant information from agent output.

    Args:
        current_output: Current agent output
        previous_outputs: List of previous agent outputs
        similarity_threshold: Threshold for considering text redundant (0.0-1.0)

    Returns:
        Filtered output with redundant sections removed
    """
    if not current_output or not previous_outputs:
        return current_output

    # Simple redundancy detection based on exact substring matching
    # In a more sophisticated implementation, you could use text similarity metrics
    lines = current_output.split("\n")
    filtered_lines = []

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            filtered_lines.append(line)
            continue

        # Check if this line (or very similar line) appears in previous outputs
        is_redundant = False
        for prev_output in previous_outputs:
            if line_stripped in prev_output:
                # Exact match
                is_redundant = True
                break

            # Check for similar lines (simple heuristic)
            for prev_line in prev_output.split("\n"):
                prev_line_stripped = prev_line.strip()
                if (
                    line_stripped
                    and prev_line_stripped
                    and len(line_stripped) > 20
                    and len(prev_line_stripped) > 20
                ):
                    # Check if one contains the other (for longer lines)
                    if (
                        line_stripped in prev_line_stripped
                        or prev_line_stripped in line_stripped
                    ):
                        is_redundant = True
                        break

            if is_redundant:
                break

        if not is_redundant:
            filtered_lines.append(line)
        else:
            logger.debug("Filtered redundant line: %s", line_stripped[:100])

    filtered_output = "\n".join(filtered_lines)

    # Calculate reduction
    original_len = len(current_output)
    filtered_len = len(filtered_output)
    if original_len > 0:
        reduction = (original_len - filtered_len) / original_len
        if reduction > 0.1:  # Only log if reduction > 10%
            logger.info(
                "Filtered redundant output: %d -> %d chars (%.1f%% reduction)",
                original_len,
                filtered_len,
                reduction * 100,
            )

    return filtered_output


def create_summary_only_output(full_output: str, max_summary_length: int = 500) -> str:
    """Create summary-only version of agent output.

    Args:
        full_output: Full agent output
        max_summary_length: Maximum length of summary

    Returns:
        Summary-only version
    """
    if not full_output:
        return ""

    # Simple summarization: take first few sentences or truncate
    sentences = full_output.split(". ")
    summary_parts = []
    current_length = 0

    for sentence in sentences:
        if current_length + len(sentence) > max_summary_length:
            break
        summary_parts.append(sentence)
        current_length += len(sentence) + 2  # +2 for ". "

    summary = ". ".join(summary_parts)
    if summary and not summary.endswith("."):
        summary += "."

    # If summary is much shorter, add note
    if len(summary) < len(full_output) * 0.3:  # Less than 30% of original
        summary += f"\n\n[Note: Output truncated from {len(full_output)} to {len(summary)} characters. Full output available in detailed logs.]"

    return summary


# ============================================================================
# EXPLORER CREW OPTIMIZATION
# ============================================================================


class ExplorerCrewMemoryOptimizer:
    """Memory optimizer for the 5-agent sequential ExplorerCrew pattern."""

    def __init__(self, crew_name: str = "ExplorerCrew"):
        self.crew_name = crew_name
        self.agent_outputs: dict[str, str] = {}
        self.incremental_storage: list[str] = []
        self.memory_baseline: dict[str, float] | None = None

    def record_agent_output(self, agent_name: str, output: str) -> None:
        """Record agent output for incremental storage."""
        self.agent_outputs[agent_name] = output

        # Store summary only for incremental storage
        summary = create_summary_only_output(output, max_summary_length=200)
        self.incremental_storage.append(f"{agent_name}: {summary}")

        # Log memory usage
        if self.memory_baseline is None:
            self.memory_baseline = get_memory_usage()

        current_mem = get_memory_usage()
        delta_mb = current_mem["rss_mb"] - (
            self.memory_baseline["rss_mb"] if self.memory_baseline else 0
        )

        logger.debug(
            "ExplorerCrew agent %s memory: RSS=%.1fMB (Δ%.1fMB)",
            agent_name,
            current_mem["rss_mb"],
            delta_mb,
        )

    def get_incremental_summary(self) -> str:
        """Get incremental summary of all agent outputs."""
        return "\n".join(self.incremental_storage)

    def cleanup_agent_outputs(self, keep_summaries_only: bool = True) -> None:
        """Clean up agent outputs to free memory."""
        if keep_summaries_only:
            # Replace full outputs with summaries
            for agent_name, output in self.agent_outputs.items():
                summary = create_summary_only_output(output, max_summary_length=200)
                self.agent_outputs[agent_name] = summary

        # Force garbage collection
        force_garbage_collection()

        current_mem = get_memory_usage()
        if self.memory_baseline:
            delta_mb = current_mem["rss_mb"] - self.memory_baseline["rss_mb"]
            logger.info(
                "ExplorerCrew memory cleanup: RSS=%.1fMB (total Δ%.1fMB from baseline)",
                current_mem["rss_mb"],
                delta_mb,
            )


# Initialize on module import
optimize_memory_settings()
