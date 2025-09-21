import asyncio
import os
from typing import AsyncIterator, TypeVar

T = TypeVar("T")

# Merge multiple streams into one stream.
# Each yielded item is a tuple: (stream_key, value).
async def amerge(**streams: AsyncIterator[T]) -> AsyncIterator[tuple[str, T]]:
    nexts: dict[asyncio.Task, str] = {
        asyncio.create_task(anext(stream)): key for key, stream in streams.items()
    }
    while nexts:
        done, _ = await asyncio.wait(nexts, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            key = nexts.pop(task)
            stream = streams[key]
            try:
                yield key, task.result()
                nexts[asyncio.create_task(anext(stream))] = key
            except StopAsyncIteration:  # Stops when all input streams are exhausted.
                pass
            except Exception as e:
                for task in nexts:
                    task.cancel()
                raise e


# ASR (Automatic Speech Recognition)

class BaseASR:
    async def transcribe(self, audio: bytes) -> str:
        raise NotImplementedError


class OpenAIASR(BaseASR):
    async def transcribe(self, audio: bytes) -> str:
        text = "transcribed text from OpenAI"
        print(f"Transcribed: '{text}'   # openai")
        return text


class DeepgramASR(BaseASR):
    async def transcribe(self, audio: bytes) -> str:
        text = "transcribed text from Deepgram"
        print(f"Transcribed: '{text}'   # deepgram")
        return text


# TTS (Text-to-Speech)

class BaseTTS:
    async def synthesize(self, text: str) -> bytes:
        raise NotImplementedError

class OpenAITTS(BaseTTS):
    async def synthesize(self, text: str) -> bytes:
        print("Synthesized audio (openai)")
        return b"binary audio from OpenAI"

class ElevenLabsTTS(BaseTTS):
    async def synthesize(self, text: str) -> bytes:
        print("Synthesized audio (elevenlabs)")
        return b"binary audio from ElevenLabs"

class AzureTTS(BaseTTS):
    async def synthesize(self, text: str) -> bytes:
        print("Synthesized audio (azure)")
        return b"binary audio from Azure"


# Provider Factories

# Return an ASR provider instance by name.
def get_asr_provider(name: str = "openai") -> BaseASR:
    name = name.lower()
    if name == "deepgram":
        return DeepgramASR()
    return OpenAIASR()

# Return a TTS provider instance by name.
def get_tts_provider(name: str = "openai") -> BaseTTS:
    name = name.lower()
    if name == "elevenlabs":
        return ElevenLabsTTS()
    if name == "azure":
        return AzureTTS()
    return OpenAITTS()


