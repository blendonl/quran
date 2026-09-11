import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.ws.session import RecitationSession
from app.ws.protocol import ErrorMessage

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/recite")
async def recite_websocket(ws: WebSocket):
    await ws.accept()

    corpus = ws.app.state.corpus
    engine_router = ws.app.state.engine_router
    prefix_index = ws.app.state.prefix_index
    ipa_database = getattr(ws.app.state, "ipa_database", None)
    noise_filter = getattr(ws.app.state, "noise_filter", None)

    if not corpus or not engine_router or not prefix_index:
        missing = []
        if not corpus:
            missing.append("corpus")
        if not engine_router:
            missing.append("engine_router")
        if not prefix_index:
            missing.append("prefix_index")
        msg = f"Server not initialized: missing {', '.join(missing)}"
        logger.warning(msg)
        await ws.send_json(ErrorMessage(message=msg).model_dump())
        await ws.close()
        return

    session = RecitationSession(
        ws, corpus, engine_router, prefix_index, ipa_database,
        noise_filter=noise_filter,
    )

    try:
        while True:
            message = await ws.receive()

            if message.get("type") == "websocket.disconnect":
                break

            if "text" in message:
                data = json.loads(message["text"])
                msg_type = data.get("type")
                logger.info("Control message: %s", msg_type)

                if msg_type == "session.start":
                    sample_rate = data.get("sample_rate", 16000)
                    encoding = data.get("encoding", "pcm_s16le")
                    surah_id = data.get("surah_id")
                    ayah_number = data.get("ayah_number")
                    logger.info(
                        "session.start: surah_id=%s ayah_number=%s sample_rate=%s encoding=%s",
                        surah_id, ayah_number, sample_rate, encoding,
                    )
                    await session.start(
                        sample_rate,
                        surah_id=surah_id,
                        ayah_number=ayah_number,
                        encoding=encoding,
                    )

                elif msg_type == "session.stop":
                    await session.stop()

            elif "bytes" in message:
                audio_bytes = message["bytes"]
                logger.debug("Audio bytes received: %d bytes", len(audio_bytes))
                await session.process_audio(audio_bytes)

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.exception("WebSocket error")
        try:
            await ws.send_json(ErrorMessage(message=str(e)).model_dump())
        except Exception:
            pass
    finally:
        await session.stop()
