# epub2audio 📗🔊

Tool for automatically converting EPub ebooks to audio using
[TTS](https://github.com/coqui-ai/TTS).

## Usage

```
usage: epub2audio [-h] [-o DIR] [--model NAME] [--speaker-wav PATH] [--language LANG] [--on-error {ask,skip,edit}] [--log-level {debug,info,warning,error,critical}] PATH [PATH ...]

Convert EPub files to audiobooks.

positional arguments:
  PATH                  input EPub files

options:
  -h, --help            show this help message and exit
  -o DIR, --output DIR  output directory
  --model NAME          model name
  --speaker-wav PATH    speaker wav file path
  --language LANG       language name
  --on-error {ask,skip,edit}
                        strategy for handling synthesizer errors
  --log-level {debug,info,warning,error,critical}
                        set log level
```

## Examples

The following command will convert `input.epub` into audio using the default
Tacotron2 synthesizer model:

```sh
epub2audio input.epub
```

The following command will convert `input.epub` into audio using
[XTTS2](https://huggingface.co/coqui/XTTS-v2) synthesizer model. This mode
requires a reference audio clip (supplied with the `--speaker-wav` command-line
option) for the synthesizer to imitate:

```sh
epub2audio --model 'tts_models/multilingual/multi-dataset/xtts_v2' \
  --speaker-wav speaker.mp3 \
  --language en \
  input.epub
```
