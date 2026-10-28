import glob
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import psutil

from usm.compat.profile_model import ClientProfile

class Candidate:
    def __init__(self, path: Path, variant_name: str, confidence: float, evidence: List[str]):
        self.path = path
        self.variant_name = variant_name
        self.confidence = confidence
        self.evidence = evidence

    def __repr__(self):
        return f"<Candidate {self.path} (variant={self.variant_name}, conf={self.confidence:.2f})>"

class DiscoveryEngine:
    def __init__(self, profile: ClientProfile):
        self.profile = profile

    def _expand_path_pattern(self, pattern: str) -> List[Path]:
        # Expand environment variables
        expanded = os.path.expandvars(pattern)
        if expanded.startswith("~"):
            expanded = str(Path.home()) + expanded[1:]
        
        # Handle Windows and Unix separators
        expanded = expanded.replace("/", os.sep).replace("\\", os.sep)

        # If wildcards are present (e.g. Packages/Claude_*/...)
        if "*" in expanded or "?" in expanded:
            matches = glob.glob(expanded)
            return [Path(m) for m in matches]
        
        return [Path(expanded)]

    def discover_candidates(self) -> List[Candidate]:
        candidates: List[Candidate] = []
        running_exes = self._get_running_process_names()

        for variant in self.profile.install_variants:
            expanded_dirs = self._expand_path_pattern(variant.config_dir)
            for d in expanded_dirs:
                target_file = d / self.profile.config.filename
                evidence = [f"Pattern '{variant.config_dir}' matched '{d}'"]
                confidence = 0.70

                # Check if process is running
                matched_process = False
                for p_name in self.profile.config.process_names:
                    if p_name.lower() in running_exes:
                        matched_process = True
                        evidence.append(f"Process '{p_name}' is currently running")
                        confidence += 0.15
                        break

                if target_file.exists():
                    confidence += 0.15
                    evidence.append("Target configuration file exists on disk")
                    candidates.append(Candidate(target_file, variant.name, min(confidence, 1.0), evidence))
                elif d.exists():
                    evidence.append("Config directory exists, but file is not yet created")
                    candidates.append(Candidate(target_file, variant.name, 0.60, evidence))

        # Sort candidates by confidence descending
        candidates.sort(key=lambda c: c.confidence, reverse=True)
        return candidates

    def _get_running_process_names(self) -> set:
        names = set()
        try:
            for p in psutil.process_iter(["name"]):
                n = p.info.get("name")
                if n:
                    names.add(n.lower())
        except Exception:
            pass
        return names

    def resolve_best_path(self, path_override: Optional[str] = None) -> Optional[Path]:
        if path_override:
            p = Path(os.path.expandvars(path_override)).expanduser().resolve()
            return p

        candidates = self.discover_candidates()
        if not candidates:
            return None
        
        # Return highest confidence candidate
        return candidates[0].path
