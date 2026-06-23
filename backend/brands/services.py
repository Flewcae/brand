"""Shared helpers used by both the generation pipeline and the content
suggestion engine to turn a BrandProfile into Claude prompt context."""


def build_brand_context_text(brand):
    parts = [f"Marka adı: {brand.name}"]
    if brand.style_description:
        parts.append(f"Stil tarifi: {brand.style_description}")
    if brand.voice_tone_description:
        parts.append(f"Ton/ses: {brand.voice_tone_description}")
    if brand.target_audience:
        parts.append(f"Hedef kitle: {brand.target_audience}")
    if brand.voice_traits:
        parts.append(f"Marka karakteri: {', '.join(brand.voice_traits)}")

    ai_context = getattr(brand, "ai_context", None)
    if ai_context:
        if ai_context.style_keywords:
            parts.append(f"Stil anahtar kelimeleri: {', '.join(ai_context.style_keywords)}")
        if ai_context.mood_descriptors:
            parts.append(f"Ruh hali: {', '.join(ai_context.mood_descriptors)}")
        if ai_context.visual_donts:
            parts.append(f"Kaçınılması gerekenler: {', '.join(ai_context.visual_donts)}")

    brand_colors = list(brand.colors.values_list("hex_value", flat=True))
    if brand_colors:
        parts.append(f"Marka renkleri: {', '.join(brand_colors)}")

    return "\n".join(parts)
