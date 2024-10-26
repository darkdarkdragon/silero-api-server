import pathlib
import os
import tempfile
import hashlib
from fastapi import FastAPI, Response, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask
from pydantic import BaseModel
import uvicorn
from silero_api_server.tts import SileroTtsService
from loguru import logger
from typing import Optional, Tuple
from pydub import AudioSegment
from num2words import num2words

module_path = pathlib.Path(__file__).resolve().parent
os.chdir(module_path)
print(f"module path: {module_path}")
SAMPLE_PATH = "samples"
SESSION_PATH = "sessions"

tts_service = SileroTtsService(
    f"{module_path}//{SAMPLE_PATH}", SESSION_PATH, languages=["en", "es", "ua"]
)
# tts_service = SileroTtsService(f"{module_path}//{SAMPLE_PATH}", SESSION_PATH, languages=['ua'])
app = FastAPI()

# Make sure the samples directory exists
if not os.path.exists(SAMPLE_PATH):
    os.mkdir(SAMPLE_PATH)

# if len(os.listdir(SAMPLE_PATH)) == 0:
#     logger.info("Samples empty, generating new samples.")
#     tts_service.generate_samples()


# app.mount(f"/samples",StaticFiles(directory=f"{module_path}//{SAMPLE_PATH}"),name='samples')
def calculate_hashes(file_path: str) -> Tuple[str, str]:
    md5_hash = hashlib.md5()
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as file:
        # Read the file in chunks to avoid loading the entire file into memory
        for chunk in iter(lambda: file.read(4096), b""):
            md5_hash.update(chunk)
            sha256_hash.update(chunk)
    return md5_hash.hexdigest(), sha256_hash.hexdigest()


origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Voice(BaseModel):
    language: str
    speaker: str
    text: str
    use_ssml: bool = False
    session: Optional[str]


class SampleText(BaseModel):
    text: Optional[str]


class Num2WordsResponse(BaseModel):
    words: str


class SpeakerDesc(BaseModel):
    name: str
    voice_id: str
    preview_url: str


#
# converter:
# - cardinal
# - ordinal
# - ordinal_num
# - year
# - currency
@app.get("/num2words")
def _num2words(num: int, lang: str, converter: str = "cardinal") -> Num2WordsResponse:
    return {"words": num2words(num, lang=lang, to=converter)}


@app.get("/tts/speakers")
def speakers(request: Request) -> dict[str, list[SpeakerDesc]]:
    voices = {
        lang: [
            {
                "name": speaker,
                "voice_id": speaker,
                "preview_url": f"{str(request.base_url)}{SAMPLE_PATH}/{speaker}.wav",
            }
            for speaker in speaker
        ]
        for lang, speaker in tts_service.get_speakers().items()
    }
    return voices


def remove_file(path: str) -> None:
    os.unlink(path)


@app.post(
    "/tts/generate",
    response_class=FileResponse,
    responses={
        200: {
            "content": {"audio/mpeg": {}},
            "description": "Return the MP3 file.",
        }
    },
)
def generate(voice: Voice) -> FileResponse:
    if voice.language == "uk":
        voice.language = "ua"
    # Clean elipses
    voice.text = voice.text.replace("*", "")
    # try:
    if 1:
        wav_file_name = tempfile.mktemp(suffix=".wav")
        logger.info(f"Gen 001 in {voice.language}")
        if voice.session:
            audio = tts_service.generate(
                voice.language,
                voice.speaker,
                voice.text,
                voice.session,
                audio_file_path=wav_file_name,
                use_ssml=voice.use_ssml,
            )
        else:
            audio = tts_service.generate(
                voice.language,
                voice.speaker,
                voice.text,
                audio_file_path=wav_file_name,
                use_ssml=voice.use_ssml,
            )
        logger.info(f"Gen 002 in {voice.language}")
        mp3_file_name = tempfile.mktemp(suffix=".mp3")
        logger.info(f"Gen 003 in {voice.language}")
        raw = AudioSegment.from_wav(audio)
        logger.info(f"Gen 004 in {voice.language}")
        raw.export(mp3_file_name, format="mp3")
        os.unlink(audio)
        logger.info(f"Gen 005 in {voice.language}")
        task = BackgroundTask(remove_file, mp3_file_name)
        md5, sha256 = calculate_hashes(mp3_file_name)
        logger.info(f"Gen 006 in {voice.language}")
        duration_in_milliseconds = len(raw)
        headers = {
            "duration": str(duration_in_milliseconds),
            "md5": md5,
            "sha256": sha256,
        }
        logger.info(f"End Generating text using speaker {voice.speaker} in {voice.language}")
        return FileResponse(
            mp3_file_name, media_type="audio/mpeg", headers=headers, background=task
        )
    # except Exception as e:
    #     logger.error(e)
    #     return HTTPException(500, voice.speaker)


# @app.get("/tts/sample")
# def play_sample(speaker: str):
#     return FileResponse(f"{SAMPLE_PATH}/{speaker}.wav")

# @app.post("/tts/generate-samples")
# def generate_samples(sample_text: Optional[str] = ""):
#     tts_service.update_sample_text(sample_text)
#     tts_service.generate_samples()
#     return Response("Generated samples",status_code=200)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
