# Beer Cap Matcher

[![CI](https://github.com/Exoodes/beer-cap-matcher/actions/workflows/ci.yml/badge.svg)](https://github.com/Exoodes/beer-cap-matcher/actions/workflows/ci.yml)

This project provides a FastAPI service for matching beer caps using image embeddings and FAISS.

## Running with Docker Compose

Build and start the services:

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`.

### Health Checks

- The API exposes a `/health` endpoint returning the service status.
- `docker-compose.yml` defines health checks for the API, PostgreSQL and MinIO services.

Use `docker compose ps` to view container health states.

## U²-Net Model

The application uses the [U²-Net](https://github.com/xuebinqin/U-2-Net) model for
background removal. By default the model weights are expected at
`models/u2net.pth`. You can download the weights with:

```bash
python scripts/download_u2net.py
```

To store the model in a different location, set the `U2NET_MODEL_PATH`
environment variable to your desired path before running the download script or
the application.

## Creating Beer Caps

The API uses `BeerCapCreateSchema` when creating new caps.
Examples of request payloads:

Creating a cap for an existing beer:

```json
{
  "filename": "cap.jpg",
  "variant_name": "special",
  "collected_date": "2024-05-01",
  "beer_id": 1
}
```

Creating a cap and a new beer in one request:

```json
{
  "filename": "new_cap.jpg",
  "beer_name": "New Lager",
  "beer_brand_name": "Acme Brewery",
  "country_name": "Germany"
}
```

Provide `beer_id` to attach the cap to an existing beer, or `beer_name` with optional brand and country information to create a new beer.

## Creating Beer and Cap Entries

The `BeerCapFacade` no longer includes the `create_beer_with_cap_and_upload`
shortcut. To add beer and cap records:

- Use `BeerCapFacade.create_cap_and_related_entities` to create a new beer and
  its cap in a single call.
- For an existing beer, first create the beer via `create_beer` from
  `src.db.crud.beer_crud` and then call
  `BeerCapFacade.create_cap_for_existing_beer_and_upload`.

Both flows upload cap images to MinIO and return the created database entries.
