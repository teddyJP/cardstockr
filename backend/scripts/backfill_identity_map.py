"""
Stub script to backfill the `card_identities` table from existing sales.

In v1, you can:
1. Scan distinct combinations of set/year/number/name from `sales`.
2. Generate a canonical `card_id` string.
3. Insert into `card_identities` with alias patterns for title parsing.
"""


def main() -> None:
    # TODO: Implement:
    # - Query distinct card-like attributes from sales
    # - Normalize and create card_id strings
    # - Insert/update CardIdentity rows
    print("backfill_identity_map.py is a placeholder. Implement mapping logic here.")


if __name__ == "__main__":
    main()

