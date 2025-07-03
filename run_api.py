import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse

from src.main import BeerCapMatcherApp
from src.similarity.image_querier import AggregatedResult

app = FastAPI(
    title="Beer Cap Matcher API",
    description="API for augmenting, embedding, indexing, and querying beer cap images.",
    version="0.1.0",
)

matcher_app = BeerCapMatcherApp()


@app.get("/")
async def root():
    return {"message": "Beer Cap Matcher API is running."}


@app.post("/augment")
async def augment():
    matcher_app.run_augmentation()
    return {"status": "Augmentation complete."}


@app.post("/generate-embeddings")
async def generate_embeddings():
    matcher_app.run_embedding_generation()
    return {"status": "Embeddings generation complete."}


@app.post("/index")
async def index():
    matcher_app.run_indexing()
    return {"status": "Indexing complete."}


@app.post("/query")
async def query(file: UploadFile = File(...), top_k: int = 5):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        results = matcher_app.run_query(tmp_path, top_k=top_k)

        response = []
        if results:
            for r in results:
                response.append(
                    {
                        "original_image": r.original_image,
                        "match_count": r.match_count,
                        "mean_distance": r.mean_distance,
                        "min_distance": r.min_distance,
                        "max_distance": r.max_distance,
                    }
                )

        return JSONResponse(content={"results": response})

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
    finally:
        file.file.close()
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)
