"""Conventional text-method pilots on the same locked Hurst evaluation units.

Sentiment, LDA and imported authentic LIWC scores retain their native scales.
All inferential dimensions enter the same-sign permutation/BH calculation.
Optional dependencies are imported only by the method that needs them.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import hashlib
import json
from pathlib import Path
import re
import time

import numpy as np
import pandas as pd

from .config import RunConfig
from .core import stage5, bh_pass
from .data import Dataset
from .select import _required_permutations, run_selection
from .validation import sha256


def empath_lexicon():
    """Load only the pinned package's supplied categories, with provenance."""
    from empath import Empath
    lexicon = Empath(backend_url=None)  # scoring is local; category generation is unused
    root = Path(lexicon.base_dir)
    dictionary = root / 'data/categories.tsv'
    expected = {}
    for line in dictionary.read_text(encoding="utf-8").splitlines():
        category, *terms = line.split('\t')
        if category in expected:raise ValueError('Duplicate supplied Empath category')
        expected[category] = set(terms)
    if {k:set(v) for k,v in lexicon.cats.items()} != expected:
        raise ValueError('Empath contains custom categories or altered supplied terms')
    categories = sorted(expected)
    meta = {'version':importlib.metadata.version('empath'),'categories':categories,
            'category_count':len(categories),'dictionary_sha256':sha256(dictionary),
            'core_sha256':sha256(root/'core.py'),'tokenizer_source_sha256':sha256(root/'helpers.py'),
            'category_family':'all supplied categories, including constant/zero categories',
            'normalized_score':'category word matches divided by all tokens; categories may overlap',
            'dictionary_path':str(dictionary),'custom_categories':False,'api_calls':0}
    return lexicon, meta


def empath_tokens(text):
    """Casefold Unicode words, retaining internal apostrophes; no stemming."""
    return re.findall(r"[^\W_]+(?:['’][^\W_]+)*", text.casefold())


def empath_scores(texts, lexicon, categories, preprocessing='word_tokens'):
    """Use Empath's own matcher and expose coverage separately from missingness."""
    if preprocessing not in {'word_tokens','package_default'}:
        raise ValueError('Unknown Empath preprocessing')
    vocabulary = {term for cat in categories for term in lexicon.cats[cat]}
    rows, coverage = [], []
    for text in texts:
        tokens = empath_tokens(text) if preprocessing=='word_tokens' else text.split()
        # A tokenized string lets the package's default tokenizer reproduce this stream exactly.
        result = lexicon.analyze(' '.join(tokens), categories=categories, normalize=True)
        rows.append(result if result is not None else {c:np.nan for c in categories})
        matches = sum(t in vocabulary for t in tokens)
        coverage.append({'tokens':len(tokens),'dictionary_matched_tokens':matches,
                         'dictionary_coverage':matches/len(tokens) if tokens else None,
                         'any_dictionary_match':matches>0})
    return pd.DataFrame(rows,columns=categories), pd.DataFrame(coverage)


def test_scores(scores, groups, halves, permutations):
    """One complete method output family; no selection by observed difference."""
    if scores.empty or not np.isfinite(scores.to_numpy(dtype=float)).all():
        raise ValueError("test_scores requires a nonempty complete finite score matrix")
    if any(((groups == g) & (halves == h)).sum() < 2 for g in (0, 1) for h in (1, 2)):
        raise ValueError("insufficient observations in a group-by-half cell")
    B, capped = _required_permutations(len(scores.columns), .05, permutations)
    results = stage5(groups, halves, {c: scores[c].to_numpy(dtype=float) for c in scores}, B=B)
    passed05 = bh_pass({c: v[2] for c, v in results.items()}, .05)
    passed10 = bh_pass({c: v[2] for c, v in results.items()}, .10)
    rows = []
    for column, (d1, d2, p) in results.items():
        values = scores[column].to_numpy(dtype=float)
        focal, ref = values[groups == 1], values[groups == 0]
        pooled = np.sqrt(((len(focal)-1)*focal.var(ddof=1) + (len(ref)-1)*ref.var(ddof=1)) /
                         (len(focal) + len(ref) - 2))
        rows.append({"dimension": column, "d1_native": d1, "d2_native": d2,
                     "mean_half_difference_native": (d1 + d2)/2, "perm_p": p,
                     "q05": column in passed05, "q10": column in passed10,
                     "focal_mean_native": float(focal.mean()), "reference_mean_native": float(ref.mean()),
                     "standardized_overall_difference": float((focal.mean()-ref.mean()) / pooled) if pooled else None})
    return rows, {"permutations": B, "permutations_capped": capped,
                  "multiplicity_family": list(scores.columns), "n_evaluable": len(scores)}


def lda_scores(discovery_texts, evaluation_texts, topic_grid, seed):
    from sklearn.feature_extraction.text import CountVectorizer
    from sklearn.decomposition import LatentDirichletAllocation

    rng = np.random.default_rng(seed)
    order = rng.permutation(len(discovery_texts))
    cut = int(.8 * len(order))
    if cut < 10 or len(order) - cut < 2:
        raise ValueError("LDA tuning needs a larger discovery pool")
    texts = np.array(discovery_texts, dtype=object)

    def vectorizer():
        return CountVectorizer(stop_words="english", min_df=2, max_df=.95)

    tune_vectorizer = vectorizer()
    train = tune_vectorizer.fit_transform(texts[order[:cut]])
    validation = tune_vectorizer.transform(texts[order[cut:]])
    valid = np.asarray(validation.sum(axis=1)).ravel() > 0
    if not valid.any():
        raise ValueError("no tuning documents contain training vocabulary")
    tuning = []
    for k in topic_grid:
        model = LatentDirichletAllocation(n_components=k, learning_method="batch", max_iter=30,
                                         random_state=seed, n_jobs=1)
        model.fit(train)
        tuning.append({"topics": k, "discovery_validation_perplexity": float(model.perplexity(validation[valid]))})
    chosen = min(tuning, key=lambda row: (row["discovery_validation_perplexity"], row["topics"]))["topics"]
    vocab = vectorizer()
    full = vocab.fit_transform(texts)
    model = LatentDirichletAllocation(n_components=chosen, learning_method="batch", max_iter=30,
                                     random_state=seed, n_jobs=1)
    model.fit(full)
    evaluation = vocab.transform(evaluation_texts)
    known_counts = np.asarray(evaluation.sum(axis=1)).ravel()
    transformed = model.transform(evaluation)
    transformed[known_counts == 0, :] = np.nan  # a prior-only topic mixture is not observed text evidence
    names = [f"topic_{i+1:02}" for i in range(chosen)]
    words = vocab.get_feature_names_out()
    topics = [{"dimension": names[i], "top_words": words[weights.argsort()[-12:][::-1]].tolist()}
              for i, weights in enumerate(model.components_)]
    metadata = {"chosen_topics": chosen, "topic_grid": topic_grid, "tuning": tuning,
                "selection": "minimum perplexity on 20% discovery-only validation; ties choose smaller K",
                "vectorizer": {"stop_words": "english", "min_df": 2, "max_df": .95},
                "training_only_vocabulary_size": len(vocab.vocabulary_),
                "evaluation_zero_vocabulary_rows": int((known_counts == 0).sum()),
                "topics": topics, "seed": seed, "learning_method": "batch", "max_iter": 30}
    return pd.DataFrame(transformed, columns=names), metadata, (vocab, model)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--method", choices=["sentiment", "lda", "liwc"], required=True)
    parser.add_argument("--config", required=True, help="portable primary contrast config")
    parser.add_argument("--reference-run", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--topic-grid", default="5,10,15,20")
    parser.add_argument("--seed", type=int, default=260026)
    parser.add_argument("--liwc-scores", help="authentic export with uid column")
    parser.add_argument("--liwc-columns", help="frozen comma-separated category family")
    parser.add_argument("--liwc-version", help="actual software/dictionary version")
    args = parser.parse_args(argv)
    if args.method == "liwc" and not all([args.liwc_scores, args.liwc_columns, args.liwc_version]):
        parser.error("LIWC requires score export, frozen category columns, and software/dictionary version")
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    cfg, _ = RunConfig.from_file(args.config)
    data = Dataset(cfg)
    reference = Path(args.reference_run).resolve()
    partition = json.loads((reference / "00_partition.json").read_text(encoding="utf-8"))
    if data.m_uid != partition["measurement_uids"] or data.m_split.tolist() != partition["measurement_split"]:
        raise ValueError("portable data do not reproduce the locked reference partition")
    if cfg.condition != "real":
        raise ValueError("baseline comparison requires real labels")
    manifest = {"status": "engineering_pilot", "arguments": vars(args), "api_calls": 0,
                "source_sha256": sha256(__file__), "dataset_sha256": sha256(cfg.dataset),
                "config_sha256": sha256(args.config), "group_direction": "focal minus reference",
                "reference_partition_sha256": sha256(reference / "00_partition.json"),
                "source_selection_code_sha256": sha256(Path(__file__).with_name("core.py")),
                "n_locked_units": len(data.m_uid), "n_discovery_units": len(data.pool),
                "multiplicity": "within each complete method output family; not joint across methods",
                "limitations": ["Pilot; no claim of baseline superiority or independent construct validity.",
                                "Scores retain native scales; they are not binary prevalence differences.",
                                "Data construction reproduces archived Discern, not all published study exclusions."]}
    if args.method == "sentiment":
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        analyzer = SentimentIntensityAnalyzer()
        # Compound alone is the frozen primary sentiment family. Components are retained as descriptive scores.
        all_scores = pd.DataFrame([analyzer.polarity_scores(text) for text in data.m_text])
        scores = all_scores[["compound"]]
        all_scores.insert(0, "uid", data.m_uid)
        all_scores.to_csv(out / "sentiment_components.csv", index=False)
        manifest["method"] = {"primary": "VADER compound", "components": "descriptive only",
                              "vader_version": importlib.metadata.version("vaderSentiment"),
                              "loaded_lexicon_text_sha256": hashlib.sha256(analyzer.lexicon_full_filepath.encode("utf-8")).hexdigest(),
                              "loaded_emoji_text_sha256": hashlib.sha256(analyzer.emoji_full_filepath.encode("utf-8")).hexdigest()}
    elif args.method == "lda":
        grid = [int(x) for x in args.topic_grid.split(",")]
        if not grid or min(grid) < 2 or len(set(grid)) != len(grid):
            raise ValueError("topic grid needs distinct integers >=2")
        scores, meta, fitted = lda_scores(data.pool.text.tolist(), data.m_text, grid, args.seed)
        import joblib
        joblib.dump(fitted, out / "fitted_lda.joblib")
        manifest["method"] = {**meta, "sklearn_version": importlib.metadata.version("scikit-learn"),
                              "scipy_version": importlib.metadata.version("scipy")}
    else:
        imported = pd.read_csv(args.liwc_scores, dtype={"uid": str})
        if "uid" not in imported or imported.uid.duplicated().any():
            raise ValueError("LIWC export needs unique uid column")
        columns = args.liwc_columns.split(",")
        if len(set(columns)) != len(columns) or "uid" in columns or any(c not in imported for c in columns):
            raise ValueError("LIWC category columns missing, duplicated or invalid")
        if not set(data.m_uid).issubset(set(imported.uid)):
            raise ValueError("LIWC export missing evaluation UIDs")
        scores = imported.set_index("uid").loc[data.m_uid, columns].apply(pd.to_numeric, errors="raise").reset_index(drop=True)
        manifest["method"] = {"version": args.liwc_version, "export_sha256": sha256(args.liwc_scores),
                              "columns": columns}
    eligible = np.isfinite(scores.to_numpy(dtype=float)).all(axis=1)
    scores.insert(0, "uid", data.m_uid)
    scores.insert(1, "evaluable", eligible)
    scores.to_csv(out / "scores.csv", index=False)
    groups, halves = data.measurement_labels()[eligible], data.m_split[eligible]
    rows, testing = test_scores(scores.drop(columns=["uid", "evaluable"]).loc[eligible], groups, halves, cfg.permutations)
    pd.DataFrame(rows).to_csv(out / "group_differences.csv", index=False)
    manifest["testing"] = testing
    manifest["excluded_evaluation_uids"] = [uid for uid, keep in zip(data.m_uid, eligible) if not keep]
    # Re-evaluate all Discern candidates on this exact method's evaluable units.
    # This produces a matched-sample comparison when LDA/LIWC omit some scores.
    measured = json.loads((reference / "03_measured.json").read_text(encoding="utf-8"))
    candidates = json.loads((reference / "02_consolidated.json").read_text(encoding="utf-8"))["candidates"]
    from types import SimpleNamespace
    shared_data = SimpleNamespace(measurement_labels=lambda: groups, m_split=halves)
    subset_measured = {cid: {"y": np.asarray(item["y"])[eligible].tolist()} for cid, item in measured.items()}
    selected = run_selection(cfg, shared_data, subset_measured, candidates)
    (out / "discern_same_evaluation_units.json").write_text(json.dumps(selected, indent=2) + "\n", encoding="utf-8")
    manifest["reference_measurement_sha256"] = sha256(reference / "03_measured.json")
    manifest["numpy_version"], manifest["pandas_version"] = np.__version__, pd.__version__
    manifest["wall_seconds"] = round(time.monotonic() - started, 3)
    manifest["output_sha256"] = {p.name: sha256(p) for p in out.iterdir() if p.is_file()}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"method": args.method, "evaluable_units": int(eligible.sum()),
                      "dimensions": len(rows), "q05_dimensions": sum(r["q05"] for r in rows),
                      "discern_q05_same_units": selected["n_validated"], "out": str(out)}, indent=2))


if __name__ == "__main__":
    main()
