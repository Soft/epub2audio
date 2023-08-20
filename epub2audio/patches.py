import logging
from TTS.tts.models.xtts import Xtts  # type: ignore
from TTS.utils.synthesizer import Synthesizer as TTSSynthesizer  # type: ignore


def _xtts_increase_tokenizer_english_char_limit(synthesizer: TTSSynthesizer) -> None:
    if not isinstance(synthesizer.tts_model, Xtts):
        return
    logging.debug("Increasing XTTS tokenizer english character limit")
    synthesizer.tts_model.tokenizer.char_limits["en"] = 350


def apply_synthesizer_patches(synthesizer: TTSSynthesizer) -> None:
    _xtts_increase_tokenizer_english_char_limit(synthesizer)
