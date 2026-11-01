"""Draft substantive matching from definitions/questions, blind to test results.

Only candidate-bank artifacts are read. The mapping is provisional, not human
adjudication, and preserves explicit unmatched families instead of forcing fits.
"""
import argparse
import csv
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from discern import keys
from discern.core import llm_json_call
from discern.validation import sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--anchors", required=True, help="reference crosswalk scaffold directory")
    parser.add_argument("--batch", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    anchor_dir = Path(args.anchors).resolve()
    with (anchor_dir / "runs.csv").open() as stream:
        reference = next(row for row in csv.DictReader(stream) if row["run_id"] == "ARCHIVE")
    with (anchor_dir / "family_memberships.csv").open() as stream:
        memberships = list(csv.DictReader(stream))
    candidates = json.loads((Path(reference["artifact_path"]) / "02_consolidated.json").read_text())["candidates"]
    reference_by_id = {c["candidate_id"]: c for c in candidates}
    families = {}
    for member in memberships:
        c = reference_by_id[member["candidate_id"]]
        record = families.setdefault(member["family_id"], {"family_id": member["family_id"], "label": member["family_label"], "members": []})
        record["members"].append({"name": c["feature_name"], "definition": c["definition"], "question": c["classification_question"]})
    jobs = json.loads(Path(args.batch).read_text())["planned_jobs"]
    keys.load_env()
    for job in jobs:
        rid = job["run_id"]
        destination = out / f"{rid}.json"
        if destination.exists():
            print(f"{rid}: existing draft preserved", flush=True)
            continue
        cfg = json.loads(Path(job["config_path"]).read_text())
        bank_path = Path(cfg["output_dir"]) / rid / "02_consolidated.json"
        if not bank_path.exists():
            print(f"{rid}: candidate bank not ready", flush=True)
            continue
        bank = json.loads(bank_path.read_text())["candidates"]
        payload = [{"candidate_id": c["candidate_id"], "name": c["feature_name"],
                    "definition": c["definition"], "question": c["classification_question"]} for c in bank]
        prompt = (
            "Draft a substantive feature-family crosswalk. You see construct definitions and binary "
            "questions only; no run/model identities, group effects, p-values or selection outcomes. "
            "Reference families can overlap. For EACH input candidate, choose at most one reference "
            "family that best captures the same substantive construct. Names need not be identical. "
            "Return relation equivalent, broader, narrower, or related. Related is allowed only for "
            "a clear common construct, not a shared word or vague general association. Do not treat "
            "management quality, role clarity, bureaucracy, communication, and hierarchy as interchangeable. "
            "Positive vs negative versions may share a broad family, but explicitly record orientation "
            "same, opposite, or mixed in that case. If no reference family fits, return family_id null "
            "and retain a short substantive family_label, relation anchor, and orientation same (self-anchor), "
            "rather than force the candidate into an existing anchor. "
            "Map ALL proposed candidates, including likely weak or redundant ones. No features may be "
            "discarded. Return only JSON with key matches, a list containing exactly one record per "
            "candidate, with candidate_id, family_id (reference ID or null), family_label, relation, "
            "orientation, and a one-sentence rationale.\n\nREFERENCE FAMILIES:\n" +
            json.dumps(list(families.values()), ensure_ascii=False) + "\n\nCANDIDATES:\n" +
            json.dumps(payload, ensure_ascii=False))
        matches = llm_json_call(prompt, "gpt-4.1", "matches", temperature=0, max_tokens=16000,
                                required=["candidate_id", "relation", "orientation", "rationale"])
        raw_dir = out / "raw_responses"
        raw_dir.mkdir(exist_ok=True)
        (raw_dir / f"{rid}.json").write_text(json.dumps(matches, indent=2) + "\n")
        expected = {c["candidate_id"] for c in bank}
        actual = [m["candidate_id"] for m in matches]
        if len(actual) != len(set(actual)) or set(actual) != expected:
            raise ValueError(f"{rid}: matching coverage failed")
        for match in matches:
            fid = match.get("family_id")
            if fid is not None and fid not in families:
                raise ValueError(f"{rid}: unknown anchor family")
            if fid is None:
                match["original_relation"] = match["relation"]
                match["original_orientation"] = match["orientation"]
                match["relation"], match["orientation"] = "anchor", "same"
            if match["relation"] not in {"equivalent", "broader", "narrower", "related", "anchor"}:
                raise ValueError(f"{rid}: invalid relation")
            if match["orientation"] not in {"same", "opposite", "mixed"}:
                raise ValueError(f"{rid}: invalid orientation")
            if fid is None and not match.get("family_label"):
                raise ValueError(f"{rid}: unmatched construct needs a label")
        result = {"run_id": rid, "status": "draft_automated_matching_requires_review",
                  "candidate_bank_sha256": sha256(bank_path), "anchor_memberships_sha256": sha256(anchor_dir / "family_memberships.csv"),
                  "script_sha256": sha256(__file__), "model": "gpt-4.1", "temperature": 0,
                  "blind_to_selection_results": True, "matches": matches}
        with destination.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
        print(f"{rid}: matched {len(matches)} candidates; unmatched {sum(m['family_id'] is None for m in matches)}", flush=True)

    # Match new constructs across runs too; otherwise a rigidity construct with
    # three different names would incorrectly become three new family rows.
    novel_path = out / "novel_groups.json"
    if novel_path.exists() or not all((out / f"{j['run_id']}.json").exists() for j in jobs):
        return
    nodes, origin = [], {}
    for job in jobs:
        rid = job["run_id"]
        cfg = json.loads(Path(job["config_path"]).read_text())
        bank = {c["candidate_id"]: c for c in json.loads((Path(cfg["output_dir"]) / rid / "02_consolidated.json").read_text())["candidates"]}
        for match in json.loads((out / f"{rid}.json").read_text())["matches"]:
            if match["family_id"] is not None:
                continue
            nid = f"N{len(nodes)+1:03}"
            c = bank[match["candidate_id"]]
            nodes.append({"item_id": nid, "name": c["feature_name"], "definition": c["definition"],
                          "question": c["classification_question"]})
            origin[nid] = {"run_id": rid, "candidate_id": match["candidate_id"]}
    groups = []
    if nodes:
        prompt = ("Group these newly appearing feature constructs into substantive crosswalk families. "
                  "You see no run/model identities, group effects or test results. Treat names as labels, "
                  "not exact-match keys. Merge only the same underlying construct or clear broader/narrower "
                  "variants. Keep distinct concepts separate even if they share vocabulary; compensation "
                  "and organizational costs are not automatically the same. Singleton groups are valid. "
                  "Every item must belong to exactly one group. Return JSON with key groups, each containing "
                  "members (list of item IDs), canonical (one member ID), family_label (short substantive label), "
                  "and rationale (one sentence).\n\n" + json.dumps(nodes))
        groups = llm_json_call(prompt, "gpt-4.1", "groups", temperature=0, max_tokens=10000,
                               required=["members", "canonical", "family_label", "rationale"])
        flattened = [nid for group in groups for nid in group["members"]]
        if len(set(flattened)) != len(flattened) or set(flattened) != set(origin):
            raise ValueError("novel-family grouping coverage failed")
        if any(group["canonical"] not in group["members"] for group in groups):
            raise ValueError("novel-family canonical not a member")
    novel_path.write_text(json.dumps({"status": "draft_blinded_new_family_grouping", "blind_to_selection_results": True,
                                     "nodes": nodes, "origin": origin, "groups": groups}, indent=2) + "\n")
    print(f"Novel constructs: {len(nodes)} candidates grouped into {len(groups)} substantive families", flush=True)


if __name__ == "__main__":
    main()
