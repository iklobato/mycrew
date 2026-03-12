"""Memory monitoring utilities for the code pipeline."""

import gc
import logging
import os
import psutil
import sys
from typing import Optional

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
    """Force garbage collection and log memory freed."""
    try:
        mem_before = get_memory_usage()

        # Collect garbage
        collected = gc.collect()

        mem_after = get_memory_usage()
        freed_mb = mem_before["rss_mb"] - mem_after["rss_mb"]

        if freed_mb > 0.1:  # Only log if significant memory was freed
            logger.info(
                "GC collected %d objects, freed %.1fMB memory (RSS: %.1fMB -> %.1fMB)",
                collected,
                freed_mb,
                mem_before["rss_mb"],
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

    def __enter__(self):
        self.mem_before = get_memory_usage()
        logger.info(
            "┌─[ MEMORY GUARD: %s ]─ Start: RSS=%.1fMB",
            self.name,
            self.mem_before["rss_mb"],
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
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

            # Force GC if memory increased significantly
            if delta_mb > 50.0:  # More than 50MB increase
                force_garbage_collection()


def optimize_memory_settings():
    """Optimize Python memory settings for better performance."""
    # Increase GC thresholds for better performance (fewer collections)
    gc.set_threshold(700, 10, 10)

    # Disable debug features in production
    if not sys.flags.debug:
        gc.disable()
        gc.enable()  # Re-enable with optimized settings

    logger.info("Memory settings optimized: GC thresholds increased")


# Initialize on module import
optimize_memory_settings()
