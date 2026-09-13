from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/surahs")
async def list_surahs(request: Request):
    corpus = request.app.state.corpus
    if not corpus:
        return {"surahs": [], "error": "Quran data not loaded"}

    surahs = [
        {
            "id": s.id,
            "name_simple": s.name_simple,
            "name_arabic": s.name_arabic,
            "verses_count": s.verses_count,
        }
        for s in corpus.surahs.values()
    ]
    return {"surahs": surahs}


@router.get("/surahs/{surah_id}/ayahs")
async def list_ayahs(surah_id: int, request: Request):
    corpus = request.app.state.corpus
    if not corpus:
        return {"ayahs": [], "error": "Quran data not loaded"}

    surah = corpus.surahs.get(surah_id)
    if not surah:
        return {"ayahs": [], "error": f"Surah {surah_id} not found"}

    ayahs = [
        {
            "surah_id": a.surah_id,
            "ayah_number": a.ayah_number,
            "text_uthmani": a.text,
        }
        for a in surah.ayahs
    ]
    return {"ayahs": ayahs}
