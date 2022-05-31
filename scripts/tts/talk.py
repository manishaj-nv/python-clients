# SPDX-FileCopyrightText: Copyright (c) 2022 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: MIT

import argparse
import time
import wave
from pathlib import Path

import riva_api
from riva_api.argparse_utils import add_connection_argparse_parameters
from riva_api.audio_io import SoundCallBack, list_output_devices


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="A speech synthesis via Riva AI Services.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--voice", help="A voice name to use.", default="English-US-Female-1")
    parser.add_argument("-o", "--output", type=Path, help="Output file .wav file to write synthesized audio.")
    parser.add_argument("--list-devices", action="store_true", help="List output audio devices indices.")
    parser.add_argument("--output-device", type=int, help="Output device to use.")
    parser.add_argument("--language-code", default='en-US', help="A language of input text.")
    parser.add_argument(
        "--sample-rate-hz", type=int, default=44100, help="Number of audio frames per second in synthesized audio.")
    parser.add_argument(
        "--stream",
        action="store_true",
        help="If this option is set, then streaming synthesis is applied. Streaming means that audio is yielded "
        "as it gets ready. If `--stream` is not set, then a synthesized audio is returned in 1 response only when "
        "all text is processed.",
    )
    parser = add_connection_argparse_parameters(parser)
    args = parser.parse_args()
    if args.output is not None:
        args.output = args.output.expanduser()
    return args


def main() -> None:
    args = parse_args()
    if args.list_devices:
        list_output_devices()
        return
    auth = riva_api.Auth(args.ssl_cert, args.use_ssl, args.server)
    service = riva_api.SpeechSynthesisService(auth)
    nchannels = 1
    sampwidth = 2
    with SoundCallBack(
        args.output_device, nchannels=nchannels, sampwidth=sampwidth, framerate=args.sample_rate_hz
    ) as sound_stream:
        try:
            if args.output is not None:
                out_f = wave.open(str(args.output), 'wb')
                out_f.setnchannels(nchannels)
                out_f.setsampwidth(sampwidth)
                out_f.setframerate(args.sample_rate_hz)
            else:
                out_f = None
            while True:
                text = input("Speak: ")
                print("Generating audio for request...")
                print(f"  > '{text}': ", end='')
                start = time.time()
                if args.stream:
                    responses = service.synthesize_online(
                        text, args.voice, args.language_code, sample_rate_hz=args.sample_rate_hz
                    )
                    first = True
                    for resp in responses:
                        stop = time.time()
                        if first:
                            print(f"Time to first audio: {(stop - start):.3f}s")
                            first = False
                        sound_stream(resp.audio)
                        if out_f is not None:
                            out_f.writeframesraw(resp.audio)
                else:
                    resp = service.synthesize(text, args.voice, args.language_code, sample_rate_hz=args.sample_rate_hz)
                    stop = time.time()
                    print(f"Time spent: {(stop - start):.3f}s")
                    sound_stream(resp.audio)
                    if out_f is not None:
                        out_f.writeframesraw(resp.audio)
        finally:
            if out_f is not None:
                out_f.close()


if __name__ == '__main__':
    main()
