"""Transparent, research-use genome evidence extraction for the ResMap prototype."""
from __future__ import annotations

import io
import math
import re
from dataclasses import asdict, dataclass
from types import SimpleNamespace
from typing import Iterable

try:
    from Bio import SeqIO
except ImportError:  # lets unit tests exercise the scoring engine without Biopython
    SeqIO = None


@dataclass
class Finding:
    feature: str
    category: str
    evidence_tier: str
    locus: str
    product: str
    contig: str
    start: int | None
    end: int | None
    weight: float
    interpretation: str


CARBAPENEMASES = {
    "KPC": 4.5, "NDM": 4.8, "VIM": 4.5, "IMP": 4.5,
    "OXA-48": 4.3, "OXA-181": 4.3, "OXA-232": 4.3,
}
AMPC = {"CMY": 2.2, "DHA": 2.2, "FOX": 2.0, "ACT": 1.8, "MIR": 1.8, "ampC": 1.5}
ESBL = {"CTX-M": 1.8, "SHV": 1.2, "TEM": 0.8}
PORINS = {"ompC": 1.0, "ompF": 1.0, "ompK35": 1.2, "ompK36": 1.2, "oprD": 1.5}
EFFLUX = {"acrA": .35, "acrB": .35, "tolC": .25, "oqxA": .4, "oqxB": .4, "mexA": .35, "mexB": .35}
REGULATORS = {"ramR": .7, "ramA": .6, "marR": .6, "marA": .5, "soxR": .5, "acrR": .6}
IRON = {
    "ybt": "yersiniabactin", "fyuA": "yersiniabactin receptor", "irp": "yersiniabactin synthesis",
    "iuc": "aerobactin synthesis", "iutA": "aerobactin receptor", "iro": "salmochelin system",
    "ent": "enterobactin synthesis", "fep": "ferric-enterobactin uptake", "fec": "ferric-citrate uptake",
    "fur": "ferric uptake regulator", "tonB": "TonB-dependent uptake", "exbB": "energy-coupled uptake",
    "exbD": "energy-coupled uptake", "sit": "iron/manganese transport",
}
MOBILE = {"integrase": "integron/phage mobility", "transposase": "mobile element", "relaxase": "conjugation", "tra": "conjugation", "plasmid": "plasmid context"}


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", (text or "").lower())


def _matches(text: str, mapping: dict[str, object]) -> list[str]:
    lowered = (text or "").lower()
    resistance_families = {"kpc","ndm","vim","imp","oxa-48","oxa-181","oxa-232","cmy","dha","fox","act","mir","ctx-m","shv","tem"}
    biological_prefixes = {"ybt","iuc","iro","ent","fep","fec","sit","tra"}
    hits = []
    for key in mapping:
        token = key.lower()
        escaped = re.escape(token).replace(r"\-", "[-_]")
        optional_bla = r"(?:bla[-_]?)?" if token in resistance_families else ""
        if token in resistance_families:
            ending = r"(?:[-_]?[0-9][a-z0-9-]*)?(?![a-z0-9])"
        elif token in biological_prefixes:
            ending = r"[a-z0-9-]*(?![a-z0-9])"
        else:
            ending = r"(?![a-z0-9])"
        if re.search(rf"(?<![a-z0-9]){optional_bla}{escaped}{ending}", lowered):
            hits.append(key)
    return hits


def _qual(feature, key: str) -> str:
    value = feature.qualifiers.get(key, [""])
    return "; ".join(value) if isinstance(value, list) else str(value)


def _resistance_annotation(evidence: str, gene: str, key: str) -> bool:
    gene_l = (gene or "").lower()
    key_l = key.lower()
    named_bla = re.search(rf"bla[-_]?{re.escape(key_l).replace(r'\-', '[-_]')}", gene_l)
    functional_text = re.search(r"beta[- ]?lactamase|carbapenemase|cephalosporinase", evidence.lower())
    return bool(named_bla or functional_text)


def _fallback_genbank_records(text: str):
    """Small dependency-free GenBank feature reader used when Biopython is unavailable."""
    records = []
    for block in text.split("\n//"):
        if "LOCUS" not in block or "FEATURES" not in block:
            continue
        locus = re.search(r"^LOCUS\s+(\S+)\s+(\d+)\s+bp", block, re.M)
        version = re.search(r"^VERSION\s+(\S+)", block, re.M)
        record_id = version.group(1) if version else (locus.group(1) if locus else "record")
        length = int(locus.group(2)) if locus else 0
        feature_text = block.split("FEATURES", 1)[1].split("ORIGIN", 1)[0]
        features = []
        current = None
        last_key = None
        for line in feature_text.splitlines()[1:]:
            match = re.match(r"^\s{5}(\S+)\s+(.+)$", line)
            if match:
                if current:
                    features.append(current)
                ftype, location_text = match.groups()
                nums = [int(x) for x in re.findall(r"\d+", location_text)]
                start = min(nums) - 1 if nums else 0
                end = max(nums) if nums else 0
                current = SimpleNamespace(type=ftype, qualifiers={}, location=SimpleNamespace(start=start, end=end))
                last_key = None
                continue
            q = re.match(r'^\s+/([A-Za-z0-9_]+)=(.*)$', line)
            if q and current:
                last_key, value = q.groups()
                current.qualifiers.setdefault(last_key, []).append(value.strip().strip('"'))
            elif current and last_key and line.strip():
                current.qualifiers[last_key][-1] += " " + line.strip().strip('"')
        if current:
            features.append(current)
        records.append(SimpleNamespace(id=record_id, seq="N" * length, features=features))
    return records


def parse_genome(data: bytes, filename: str) -> tuple[list[Finding], dict]:
    """Parse annotated GenBank, or identify an unannotated FASTA without inventing genes."""
    text = data.decode("utf-8", errors="replace")
    lower = filename.lower()
    is_genbank = lower.endswith((".gb", ".gbk", ".gbff", ".genbank")) or text.lstrip().startswith("LOCUS")
    if not is_genbank:
        seqs = ["".join(line.strip() for line in block.splitlines()[1:]) for block in text.split(">") if block.strip()]
        return [], {"format": "FASTA", "annotated": False, "records": len(seqs), "bases": sum(map(len, seqs)), "message": "Sequence-only upload: run PGAP/AMRFinderPlus or upload GenBank/AMRFinderPlus output before gene-level interpretation."}
    records = list(SeqIO.parse(io.StringIO(text), "genbank")) if SeqIO is not None else _fallback_genbank_records(text)
    findings: list[Finding] = []
    cds_count = 0
    for record in records:
        for feature in record.features:
            if feature.type not in {"CDS", "gene", "mobile_element", "repeat_region"}:
                continue
            if feature.type == "CDS":
                cds_count += 1
            gene = _qual(feature, "gene") or _qual(feature, "locus_tag")
            product = _qual(feature, "product")
            note = _qual(feature, "note")
            evidence = " ".join([gene, product, note])
            location = feature.location
            start = int(location.start) + 1 if location else None
            end = int(location.end) if location else None
            common = dict(locus=gene or "—", product=product or note or "—", contig=record.id, start=start, end=end)
            for key in _matches(evidence, CARBAPENEMASES):
                if not _resistance_annotation(evidence, gene, key):
                    continue
                findings.append(Finding(key, "Resistance", "Obvious", weight=CARBAPENEMASES[key], interpretation="Acquired carbapenemase; strong genomic resistance evidence.", **common))
            for key in _matches(evidence, AMPC):
                if not _resistance_annotation(evidence, gene, key):
                    continue
                findings.append(Finding(key, "Resistance", "Supporting / hidden", weight=AMPC[key], interpretation="AmpC-family beta-lactamase; carbapenem effect depends on expression, permeability and phenotype.", **common))
            for key in _matches(evidence, ESBL):
                if not _resistance_annotation(evidence, gene, key):
                    continue
                findings.append(Finding(key, "Resistance", "Supporting / hidden", weight=ESBL[key], interpretation="Beta-lactamase family; allele and phenotype must be confirmed.", **common))
            for key in _matches(evidence, PORINS):
                if not (_norm(gene) == _norm(key) or ("porin" in product.lower() and _norm(key) in _norm(product))):
                    continue
                disrupted = any(word in evidence.lower() for word in ("truncated", "frameshift", "pseudogene", "interrupted", "premature stop"))
                findings.append(Finding(key, "Permeability", "Supporting / hidden" if disrupted else "Potential", weight=PORINS[key] if disrupted else .15, interpretation="Potential porin loss/disruption." if disrupted else "Porin annotated; intact presence alone does not establish reduced permeability.", **common))
            for key in _matches(evidence, EFFLUX):
                if _norm(gene) != _norm(key):
                    continue
                findings.append(Finding(key, "Efflux", "Potential", weight=EFFLUX[key], interpretation="Efflux component detected; expression or regulatory evidence is required.", **common))
            for key in _matches(evidence, REGULATORS):
                if _norm(gene) != _norm(key):
                    continue
                disrupted = any(word in evidence.lower() for word in ("truncated", "frameshift", "pseudogene", "interrupted"))
                findings.append(Finding(key, "Regulation", "Supporting / hidden" if disrupted else "Potential", weight=REGULATORS[key] if disrupted else .15, interpretation="Regulator disruption may alter efflux/permeability." if disrupted else "Regulator detected; sequence comparison is required to infer activation.", **common))
            for key in _matches(gene, IRON):
                findings.append(Finding(key, "Iron / uptake", "Context", weight=0, interpretation=IRON[key], **common))
            mobile_evidence = gene if _matches(gene, {"tra": "conjugation"}) else evidence
            for key in _matches(mobile_evidence, MOBILE):
                if key == "tra" and not _matches(gene, {"tra": "conjugation"}):
                    continue
                findings.append(Finding(key, "Mobile element", "Context", weight=0, interpretation=MOBILE[key], **common))
    deduped = []
    seen = set()
    for finding in findings:
        signature = (finding.feature, finding.category, finding.contig, finding.start, finding.end)
        if signature not in seen:
            seen.add(signature)
            deduped.append(finding)
    return deduped, {"format": "GenBank", "annotated": cds_count > 0, "records": len(records), "bases": sum(len(r.seq) for r in records), "cds": cds_count, "message": "Annotation-derived findings; absence is not proof of susceptibility."}


def score_findings(findings: Iterable[Finding], mic_rows: list[dict] | None = None) -> dict:
    findings = list(findings)
    # Avoid counting repeated annotations of the same mechanism as independent proof.
    mechanism_max: dict[str, float] = {}
    for f in findings:
        if f.category in {"Resistance", "Permeability", "Efflux", "Regulation"}:
            mechanism_max[f.feature] = max(mechanism_max.get(f.feature, 0), f.weight)
    z = -2.2 + sum(mechanism_max.values())
    names = set(mechanism_max)
    has_ampc = any(k in names for k in AMPC)
    has_esbl = any(k in names for k in ESBL)
    has_disrupted_porin = any(f.category == "Permeability" and f.weight >= 1 for f in findings)
    if has_ampc and has_disrupted_porin:
        z += 2.0
    if has_esbl and has_disrupted_porin:
        z += 1.4
    mic_rows = mic_rows or []
    resistant_labels = sum(str(r.get("interpretation", "")).upper() == "R" for r in mic_rows)
    if resistant_labels:
        z += min(1.0, .25 * resistant_labels)
    score = round(100 / (1 + math.exp(-max(-8, min(8, z)))))
    band = "Limited" if score < 25 else "Emerging" if score < 50 else "Substantial" if score < 75 else "Strong"
    return {"score": score, "band": band, "linear_predictor": round(z, 2), "mechanisms": mechanism_max, "synergy_ampc_porin": has_ampc and has_disrupted_porin, "synergy_esbl_porin": has_esbl and has_disrupted_porin, "labelled_mic_count": len(mic_rows), "method": "Uncalibrated weighted evidence score with logistic transform; not a clinical susceptibility prediction."}


def findings_as_dicts(findings: Iterable[Finding]) -> list[dict]:
    return [asdict(f) for f in findings]
