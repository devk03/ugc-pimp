import os
import time
import argparse
from typing import List, Optional, Tuple

from dotenv import load_dotenv
from supabase import create_client, Client
from openai import OpenAI


def get_env(key: str, fallback: Optional[str] = None) -> Optional[str]:
    value = os.getenv(key)
    return value if value else fallback


def init_supabase() -> Client:
    supabase_url = get_env("SUPABASE_URL")
    # Prefer service key for unrestricted updates
    supabase_key = get_env("SUPABASE_SERVICE_KEY", get_env("SUPABASE_KEY"))
    if not supabase_url or not supabase_key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY/SUPABASE_KEY")
    return create_client(supabase_url, supabase_key)


def init_openai() -> OpenAI:
    api_key = get_env("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY")
    return OpenAI(api_key=api_key)


def generate_embedding(client: OpenAI, text: str) -> List[float]:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    vec = response.data[0].embedding
    # Ensure a plain Python list of floats
    return list(vec)


def fetch_batch(supabase: Client, limit: int) -> List[dict]:
    # Select rows missing embedding but with non-null description
    # Supabase-py exposes the `is_` filter for PostgREST `is` operator
    query = (
        supabase.table("contact")
        .select("id, description")
        .is_("embedding", "null")
        .not_.is_("description", "null")
        .limit(limit)
    )
    res = query.execute()
    return res.data or []


def update_embedding(supabase: Client, contact_id: str, embedding: List[float]) -> None:
    supabase.table("contact").update({"embedding": embedding}).eq("id", contact_id).execute()


def backfill_embeddings(
    batch_size: int = 50,
    max_rows: Optional[int] = None,
    sleep_s: float = 0.0,
) -> Tuple[int, int]:
    """
    Returns: (processed_count, updated_count)
    """
    load_dotenv()
    supabase = init_supabase()
    openai_client = init_openai()

    processed_total = 0
    updated_total = 0

    while True:
        remaining = None if max_rows is None else max_rows - processed_total
        if remaining is not None and remaining <= 0:
            break

        take = batch_size if remaining is None else max(0, min(batch_size, remaining))
        if take == 0:
            break

        batch = fetch_batch(supabase, take)
        if not batch:
            break

        for row in batch:
            processed_total += 1
            contact_id = row.get("id")
            description = (row.get("description") or "").strip()

            if not description:
                continue

            try:
                # Safety: limit length to avoid excessive tokenization
                text = description[:8000]
                embedding = generate_embedding(openai_client, text)
                update_embedding(supabase, contact_id, embedding)
                updated_total += 1
            except Exception as e:
                print(f"⚠️  Failed to embed contact {contact_id}: {e}")

            if sleep_s > 0:
                time.sleep(sleep_s)

    return processed_total, updated_total


def main():
    parser = argparse.ArgumentParser(description="Backfill contact embeddings using OpenAI")
    parser.add_argument("--batch-size", type=int, default=50, help="Rows per batch")
    parser.add_argument("--max-rows", type=int, default=None, help="Maximum rows to process")
    parser.add_argument("--sleep", type=float, default=0.0, help="Sleep seconds between rows")
    args = parser.parse_args()

    print("Starting backfill of contact embeddings...")
    processed, updated = backfill_embeddings(
        batch_size=args.batch_size,
        max_rows=args.max_rows,
        sleep_s=args.sleep,
    )
    print(f"Done. Processed: {processed}, Updated: {updated}")


if __name__ == "__main__":
    main()


