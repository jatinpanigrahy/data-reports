"""Deterministic generator for canonical sample transaction dataset.

Generates data/sample_expenses.csv matching the specifications in docs/SAMPLE_DATA_SPEC.md:
- Exactly 250 transaction rows spanning 2026-01-01 through 2026-03-31 (Q1 2026).
- Realistic categorical distribution, vendors, departments, and amounts.
- Controlled edge cases: currency formatting variants, accounting refunds/credits,
  mixed date notations, and text variations.
- Fixed random seed (42) producing identical, verifiable golden metrics.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import random
from typing import Any


DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_expenses.csv"


def partition_sum(needed_sum: float, n: int, min_val: float, max_val: float) -> list[float]:
    """Partition a target sum into n amounts bounded within [min_val, max_val].

    Uses base mean allocation with penny-exact rounding followed by bounded
    pairwise transfers to produce natural financial variation.
    """
    assert needed_sum >= n * min_val, f"Target sum {needed_sum} is below lower bound {n * min_val}"
    assert needed_sum <= n * max_val, f"Target sum {needed_sum} exceeds upper bound {n * max_val}"

    base = round(needed_sum / n, 2)
    amounts = [base] * n
    diff = round(needed_sum - sum(amounts), 2)
    cents = int(round(diff * 100))
    step = 1 if cents > 0 else -1
    idx = 0
    while cents != 0:
        amounts[idx % n] = round(amounts[idx % n] + step * 0.01, 2)
        cents -= step
        idx += 1

    for _ in range(n * 30):
        i, j = random.sample(range(n), 2)
        max_down = amounts[i] - min_val
        max_up = max_val - amounts[j]
        max_transfer = min(max_down, max_up)
        if max_transfer > 1.0:
            delta = round(random.uniform(0.5, max_transfer * 0.7), 2)
            amounts[i] = round(amounts[i] - delta, 2)
            amounts[j] = round(amounts[j] + delta, 2)

    assert round(sum(amounts), 2) == round(needed_sum, 2)
    assert all(min_val <= x <= max_val for x in amounts)
    return amounts


def generate_records(seed: int = 42) -> list[dict[str, Any]]:
    """Generate 250 deterministic canonical transaction records."""
    random.seed(seed)

    vendors: dict[str, list[tuple[str, str]]] = {
        "Cloud Infrastructure": [
            ("Amazon Web Services Hosting", "Engineering"),
            ("AWS EC2 On-Demand Compute", "Engineering"),
            ("AWS S3 Storage Standard Tier", "Engineering"),
            ("AWS RDS Aurora Multi-AZ", "Engineering"),
            ("Datadog Infrastructure Monitoring", "Engineering"),
            ("Datadog APM Host Monitoring", "Engineering"),
            ("GCP Cloud Storage Coldline", "Engineering"),
            ("GCP Kubernetes Engine", "Engineering"),
            ("Azure Active Directory Premium", "Operations"),
            ("Azure Virtual Desktop Infrastructure", "Operations"),
        ],
        "Software & SaaS": [
            ("GitHub Enterprise Seats", "Engineering"),
            ("GitHub Copilot Business Seats", "Engineering"),
            ("Slack Enterprise Grid Subscription", "Operations"),
            ("Slack Technologies Seat Adjustment", "Operations"),
            ("Notion Team Workspace", "Product"),
            ("Figma Design Organization Plan", "Design"),
            ("Figma Enterprise Design System", "Design"),
            ("Jira Software Premium", "Engineering"),
            ("Atlassian Confluence Standard", "Operations"),
            ("PagerDuty Incident Response", "Engineering"),
        ],
        "Travel & Logistics": [
            ("Delta Air Lines Flight SFO-JFK", "Sales"),
            ("Delta Air Lines SFO-SEA Roundtrip", "Sales"),
            ("United Airlines Client Onsite Travel", "Sales"),
            ("United Airlines Chicago Board Meeting", "Executive"),
            ("Marriott Marquis Hotel Stay", "Sales"),
            ("Marriott Downtown Conference Lodging", "Executive"),
            ("Uber Technologies Airport Rides", "Sales"),
            ("Uber For Business Team Logistics", "Operations"),
        ],
        "Professional Services": [
            ("Deloitte Advisory Consulting", "Executive"),
            ("Deloitte Technical Audit Services", "Operations"),
            ("Cooley LLP Corporate Governance", "Legal"),
            ("Cooley LLP Intellectual Property Retainer", "Legal"),
            ("Fractional CFO Strategic Retainer", "Executive"),
            ("Legal Counsel Quarterly Retainer", "Executive"),
            ("Tax Strategy Advisory Retainer", "Finance"),
        ],
        "Office Equipment": [
            ("Apple Store MacBook Pro 16", "Engineering"),
            ("Apple Store Display Hardware", "Design"),
            ("Apple Store iPad Pro Display", "Engineering"),
            ("Herman Miller Aeron Chairs", "Operations"),
            ("Herman Miller Ergonomic Desks", "Operations"),
            ("CDW Logistics Network Switch", "Engineering"),
            ("CDW Server Rack Accessories", "Operations"),
            ("Ergonomic Chairs and Monitors", "Operations"),
        ],
    }

    # Explicit fixed rows required by golden test specifications and edge-case contracts
    fixed_rows: list[dict[str, Any]] = [
        # Rank 2 - Jan 4
        {"date": "2026-01-04", "category": "Cloud Infrastructure", "amount": 14250.00, "description": "Amazon Web Services Hosting", "department": "Engineering", "fmt": '"$14,250.00"', "month": 1},
        # Spec rows (Jan 5 - Jan 15)
        {"date": "2026-01-05", "category": "Software & SaaS", "amount": 1200.00, "description": "GitHub Enterprise 50 Seats", "department": "Engineering", "fmt": '"$1,200.00"', "month": 1},
        {"date": "2026-01-08", "category": "Travel & Logistics", "amount": 840.50, "description": "Delta Airlines Flight SFO-JFK", "department": "Sales", "fmt": "840.50", "month": 1},
        {"date": "2026-01-12", "category": "Professional Services", "amount": 4500.00, "description": "Legal Counsel Quarterly Retainer", "department": "Executive", "fmt": '"$4,500.00"', "month": 1},
        {"date": "2026-01-15", "category": "Office Equipment", "amount": 349.99, "description": "Ergonomic Chairs and Monitors", "department": "Operations", "fmt": "349.99", "month": 1},
        # Trailing spaces edge case
        {"date": "2026-01-20", "category": "Software & SaaS", "amount": 3100.00, "description": "Figma Enterprise Design System", "department": "Design", "fmt": '" $3,100.00 "', "month": 1},
        # Accounting credit / refund edge case
        {"date": "2026-01-28", "category": "Travel & Logistics", "amount": -450.00, "description": "Delta Air Lines Flight Cancellation Refund", "department": "Sales", "fmt": '"-$450.00"', "month": 1},

        # Month 2 fixed rows
        # Rank 3
        {"date": "2026-02-18", "category": "Cloud Infrastructure", "amount": 11500.00, "description": "GCP BigQuery Annual Reservation", "department": "Engineering", "fmt": '"$11,500.00"', "month": 2},
        # Rank 4
        {"date": "2026-02-28", "category": "Professional Services", "amount": 8200.00, "description": "Cooley LLP Regulatory Filings", "department": "Legal", "fmt": '"$8,200.00"', "month": 2},
        # Parenthetical accounting negative edge case
        {"date": "2026-02-12", "category": "Software & SaaS", "amount": -125.00, "description": "Slack Technologies Seat Adjustment Credit", "department": "Operations", "fmt": '"(125.00)"', "month": 2},
        # US slash date edge case
        {"date": "02/14/2026", "category": "Office Equipment", "amount": 540.00, "description": "Apple Store iPad Pro Display", "department": "Engineering", "fmt": "540.00", "month": 2, "_sort_date": "2026-02-14"},
        # Lowercase category edge case
        {"date": "2026-02-22", "category": "cloud infrastructure", "amount": 890.00, "description": "Datadog APM Host Monitoring", "department": "Engineering", "fmt": "890.00", "month": 2, "_canonical_cat": "Cloud Infrastructure"},

        # Month 3 fixed rows
        # Rank 1
        {"date": "2026-03-12", "category": "Cloud Infrastructure", "amount": 14850.00, "description": "Amazon Web Services Q1 Compute", "department": "Engineering", "fmt": '"$14,850.00"', "month": 3},
        # Rank 5
        {"date": "2026-03-24", "category": "Professional Services", "amount": 7500.00, "description": "Deloitte Systems Integration", "department": "Operations", "fmt": '"$7,500.00"', "month": 3},
        # Long vendor description edge case (table text wrapping)
        {"date": "2026-03-05", "category": "Professional Services", "amount": 3800.00, "description": "Comprehensive Multi-Cloud Security Assessment and Pen Testing Retainer Phase 1", "department": "Engineering", "fmt": '"$3,800.00"', "month": 3},
        # Uppercase category edge case
        {"date": "2026-03-18", "category": "SOFTWARE & SAAS", "amount": 450.00, "description": "Notion Team Workspace", "department": "Product", "fmt": "450.00", "month": 3, "_canonical_cat": "Software & SaaS"},
    ]

    # Target matrix: (category, month) -> (total_row_count, total_sum, min_spend, max_spend)
    targets: dict[tuple[str, int], tuple[int, float, float, float]] = {
        ("Cloud Infrastructure", 1): (24, 29150.00, 300.0, 1500.0),
        ("Cloud Infrastructure", 2): (23, 26400.00, 300.0, 1500.0),
        ("Cloud Infrastructure", 3): (28, 30900.00, 300.0, 1500.0),

        ("Software & SaaS", 1): (29, 22200.00, 100.0, 1800.0),
        ("Software & SaaS", 2): (28, 17500.00, 100.0, 1800.0),
        ("Software & SaaS", 3): (30, 15300.00, 100.0, 1800.0),

        ("Professional Services", 1): (8, 7800.00, 200.0, 1500.0),
        ("Professional Services", 2): (8, 12200.00, 200.0, 1500.0),
        ("Professional Services", 3): (9, 15000.00, 200.0, 1500.0),

        ("Travel & Logistics", 1): (13, 8805.50, 150.0, 1500.0),
        ("Travel & Logistics", 2): (12, 8100.00, 150.0, 1500.0),
        ("Travel & Logistics", 3): (13, 8094.50, 150.0, 1500.0),

        ("Office Equipment", 1): (8, 6000.00, 150.0, 1200.0),
        ("Office Equipment", 2): (8, 5800.00, 150.0, 1200.0),
        ("Office Equipment", 3): (9, 5185.50, 150.0, 1200.0),
    }

    cell_fixed: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for r in fixed_rows:
        cat = r.get("_canonical_cat", r["category"])
        cell = (cat, r["month"])
        cell_fixed.setdefault(cell, []).append(r)

    all_rows: list[dict[str, Any]] = []

    for (cat, month), (total_cnt, total_sum, min_val, max_val) in targets.items():
        fixed = cell_fixed.get((cat, month), [])
        needed_cnt = total_cnt - len(fixed)
        needed_sum = round(total_sum - sum(f["amount"] for f in fixed), 2)
        assert needed_cnt > 0

        amounts = partition_sum(needed_sum, needed_cnt, min_val, max_val)
        vendor_list = vendors[cat]

        for amt in amounts:
            # For January, assign days 16..31 so the first 5 records match SAMPLE_DATA_SPEC
            if month == 1:
                day = random.randint(16, 31)
            elif month == 2:
                day = random.randint(1, 28)
            else:
                day = random.randint(1, 31)

            date_str = f"2026-0{month}-{day:02d}"
            v_desc, v_dept = random.choice(vendor_list)

            # Randomize currency format representation
            if random.random() < 0.6:
                fmt_amt = f'"${amt:,.2f}"'
            else:
                fmt_amt = f"{amt:.2f}"

            all_rows.append({
                "date": date_str,
                "category": cat,
                "amount": amt,
                "description": v_desc,
                "department": v_dept,
                "fmt": fmt_amt,
                "month": month,
                "_sort_date": date_str,
            })

    for r in fixed_rows:
        sort_date = r.get("_sort_date", r["date"])
        r["_sort_date"] = sort_date
        all_rows.append(r)

    all_rows.sort(key=lambda x: x["_sort_date"])
    return all_rows


def write_sample_csv(output_path: Path, seed: int = 42) -> None:
    """Generate and write the canonical sample CSV to the specified destination."""
    rows = generate_records(seed)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("Date,Category,Amount,Description,Department\n")
        for r in rows:
            f.write(f"{r['date']},{r['category']},{r['fmt']},{r['description']},{r['department']}\n")


def main() -> None:
    """CLI entry point for sample data generator script."""
    parser = argparse.ArgumentParser(description="Generate canonical sample transaction dataset.")
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Target output CSV file path (default: data/sample_expenses.csv)",
    )
    parser.add_argument(
        "-s", "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic generation (default: 42)",
    )
    args = parser.parse_args()

    write_sample_csv(args.output, args.seed)

    # Count lines
    with open(args.output, "r", encoding="utf-8") as f:
        line_count = sum(1 for _ in f)

    print(f"Generated {line_count - 1} records ({line_count} lines) -> {args.output}")


if __name__ == "__main__":
    main()
