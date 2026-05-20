from __future__ import annotations

from app.agents.state import StyleGraphState
from app.providers.tracing import TraceRecorder


class ImagePromptAgent:
    node_name = "ImagePromptAgent"

    def __init__(self, tracer: TraceRecorder) -> None:
        self.tracer = tracer

    async def run(self, state: StyleGraphState) -> StyleGraphState:
        if state.selected_outfit is None:
            raise ValueError("Selected outfit is required before image prompting")
        item_brief = "\n".join(
            f"- {item.category.value}: {item.title}; source={item.marketplace.value}; image={item.image_url}; reason={item.match_reason}"
            for item in state.selected_outfit.items
        )
        prompt = f"""Create a realistic full-body fashion try-on image.

Primary objective: preserve the uploaded person's identity, face, skin tone, hairstyle, body proportions, and natural posture.
Dress the person in the selected outfit while keeping garment category, main color, silhouette, and material faithful to product references.

Selected outfit:
{item_brief}

Quality requirements:
- Full body visible, one person only, no text, no watermark.
- Natural lighting, realistic fit, no distorted limbs or duplicated body parts.
- Do not add garments that are not listed.
- If identity and garment fidelity conflict, prioritize identity and body realism.
"""
        self.tracer.record(state.task_id, self.node_name, "prompt_created", {"prompt": prompt})
        return state.model_copy(update={"image_prompt": prompt})

