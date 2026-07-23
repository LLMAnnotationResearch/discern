"""Generate a small SYNTHETIC demo dataset for discern (no real data, no API).

Two groups of short product blurbs: group 1 ("focal") skews toward fresh/consumable/food language,
group 0 toward durable/hardware/tools — with deliberate vocabulary overlap and noise so the contrast
is real but not trivial. This is only a toy so you can watch the pipeline discover and validate a
feature end to end; the numbers mean nothing.

    python make_demo_data.py        ->  demo.csv  (400 rows, 200/group)
"""
import csv
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent / "demo.csv"
N_PER_GROUP = 200
SEED = 7

FOCAL = {  # group 1: consumable / food-leaning
    "head": ["fresh", "organic", "homemade", "artisan", "local", "seasonal", "handmade", "small-batch"],
    "noun": ["bakery goods", "produce stand", "coffee roast", "juice blend", "spice mix", "cheese board",
             "meal kit", "snack box", "tea selection", "jam and preserves"],
    "tail": ["sold at the weekend market", "delivered fresh daily", "made in small batches",
             "for everyday households", "packaged to order", "from a family kitchen"],
}
REFERENCE = {  # group 0: durable / hardware-leaning
    "head": ["heavy-duty", "industrial", "precision", "galvanized", "modular", "reinforced", "welded", "machined"],
    "noun": ["steel fittings", "power tools", "hardware kit", "metal brackets", "pipe fixtures",
             "engine parts", "bearing assembly", "fastener set", "electrical conduit", "cutting blades"],
    "tail": ["for the construction trade", "built to industrial spec", "sold to contractors",
             "rated for heavy loads", "shipped by the pallet", "for workshop use"],
}
# a few overlapping/ambiguous blurbs shared by both groups so the signal isn't perfectly separable
NEUTRAL = ["general goods and supplies", "assorted retail items", "wholesale and resale",
           "mixed inventory for local shops", "seasonal specials and gifts"]


def blurb(rng, kit):
    if rng.random() < 0.12:                      # 12% neutral/overlap noise
        return rng.choice(NEUTRAL)
    return f"{rng.choice(kit['head'])} {rng.choice(kit['noun'])} {rng.choice(kit['tail'])}"


def main():
    rng = random.Random(SEED)
    rows = []
    for group, kit in ((1, FOCAL), (0, REFERENCE)):
        for i in range(N_PER_GROUP):
            rows.append({"id": f"g{group}_{i}", "group": group, "text": blurb(rng, kit)})
    rng.shuffle(rows)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "group", "text"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {OUT}  (columns: id, group, text; group 1=focal, 0=reference)")


if __name__ == "__main__":
    main()
