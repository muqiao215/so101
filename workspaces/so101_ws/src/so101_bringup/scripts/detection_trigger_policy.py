#!/usr/bin/env python3
"""Pure detection-trigger policy for task executor orchestration."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple


DetectionCandidate = Tuple[str, float]


@dataclass
class TriggerDecision:
    category: str
    template_id: str
    request_id: str


class DetectionTriggerPolicy:
    def __init__(
        self,
        *,
        enabled: bool,
        threshold: float,
        cooldown_sec: float,
        template_map: Dict[str, str],
    ) -> None:
        self.enabled = bool(enabled)
        self.threshold = float(threshold)
        self.cooldown_sec = float(cooldown_sec)
        self.template_map = {
            str(category).strip().lower(): str(template_id).strip()
            for category, template_id in template_map.items()
            if str(category).strip() and str(template_id).strip()
        }
        self._last_trigger_time = 0.0
        self._last_trigger_category = ""

    def select_category(
        self,
        candidates: Sequence[DetectionCandidate],
        *,
        expected_category: str = "",
    ) -> Optional[str]:
        normalized_expected = str(expected_category).strip().lower()
        matched: List[DetectionCandidate] = []
        for category, confidence in candidates:
            normalized_category = str(category).strip().lower()
            if not normalized_category:
                continue
            try:
                normalized_confidence = float(confidence)
            except Exception:
                normalized_confidence = 0.0
            if normalized_confidence < self.threshold:
                continue
            if normalized_expected and normalized_category != normalized_expected:
                continue
            matched.append((normalized_category, normalized_confidence))

        if not matched:
            return None

        matched.sort(key=lambda item: item[1], reverse=True)
        return matched[0][0]

    def try_trigger(
        self,
        candidates: Sequence[DetectionCandidate],
        *,
        busy: bool,
        now: float,
    ) -> Optional[TriggerDecision]:
        if not self.enabled or busy:
            return None

        category = self.select_category(candidates)
        if not category:
            return None

        template_id = self.template_map.get(category)
        if not template_id:
            return None

        if (
            category == self._last_trigger_category
            and now - self._last_trigger_time < self.cooldown_sec
        ):
            return None

        self._last_trigger_category = category
        self._last_trigger_time = now
        return TriggerDecision(
            category=category,
            template_id=template_id,
            request_id=f"det-{category}-{int(now * 1000)}",
        )
