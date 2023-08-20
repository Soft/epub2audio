import logging
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from . import patches

from TTS.utils.manage import ModelManager  # type: ignore
from TTS.utils.synthesizer import Synthesizer as TTSSynthesizer  # type: ignore


class Synthesizer:
    def __init__(
        self,
        *,
        model_name: str,
        vocoder_name: str | None = None,
        speaker_wav: str | None = None,
        language_name: str | None = None,
    ) -> None:
        self.speaker_wav = speaker_wav
        self.language_name = language_name

        with _maybe_silence_output(logging.root.level > logging.DEBUG):
            self.synthesizer = self._create_synthesizer(model_name, vocoder_name)

    def _create_synthesizer(
        self,
        model_name: str,
        vocoder_name: str | None,
    ) -> TTSSynthesizer:
        model_manager = ModelManager()
        tts_checkpoint, tts_config_path, model = model_manager.download_model(
            model_name
        )

        # Model with multiple files
        if isinstance(model.get("model_url"), list):
            model_dir = tts_checkpoint
            tts_checkpoint = None
            tts_config_path = None
        else:
            model_dir = None

        if vocoder_name is None:
            vocoder_name = model.get("default_vocoder")

        if vocoder_name is not None:
            vocoder_checkpoint, vocoder_config, _ = model_manager.download_model(
                vocoder_name
            )
        else:
            vocoder_checkpoint = None
            vocoder_config = None

        synthesizer = TTSSynthesizer(
            tts_checkpoint=tts_checkpoint,
            tts_config_path=tts_config_path,
            vocoder_checkpoint=vocoder_checkpoint,
            vocoder_config=vocoder_config,
            model_dir=model_dir,
        )
        patches.apply_synthesizer_patches(synthesizer)
        return synthesizer

    def generate_to_file(self, text: str, output_path: Path) -> None:
        logging.debug(f"Synthesizing {text!r}")
        with _maybe_silence_output(logging.root.level > logging.DEBUG):
            wav_data = self.synthesizer.tts(
                text=text,
                language_name=self.language_name
                if self.language_name is not None
                else "",
                speaker_wav=[self.speaker_wav]
                if self.speaker_wav is not None
                else None,
                speaker_name=None,
            )
            self.synthesizer.save_wav(wav_data, str(output_path))


@contextmanager
def _maybe_silence_output(silence: bool) -> Iterator[None]:
    if silence:
        with open(os.devnull, "w") as handle:
            original = sys.stdout
            sys.stdout = handle
            try:
                yield
            finally:
                sys.stdout = original
    else:
        yield
