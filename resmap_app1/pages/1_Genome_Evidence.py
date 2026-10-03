from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from brand import apply_brand
from resmap_core import Finding, findings_as_dicts, parse_genome, score_findings

apply_brand()
st.markdown("""
<style>
html, body, [class*="css"] {font-family:"Trebuchet MS","Arial Rounded MT Bold",Arial,sans-serif;}
.block-container {padding-top: 1.5rem; max-width: 1500px;}
.hero {background:linear-gradient(110deg,#087F7A,#20A39E); color:white; padding:1.7rem 2rem; border-radius:26px; border-bottom:8px solid #E6AD27;}
.hero h1 {font-size:2.65rem; margin:0; letter-spacing:-.03em;}
.hero p {font-size:1.08rem; margin:.45rem 0 0; color:#F9E6A8;}
.callout {border-left:6px solid #F28C28; background:#FFF4D6; padding:.8rem 1rem; border-radius:8px;}
.journey {background:white; border:2px solid #B7DEDA; border-top:7px solid #E6AD27; padding:1rem; border-radius:20px; min-height:145px;}
.journey b {color:#087F7A; font-size:1.03rem;}
.small {color:#526B7D; font-size:.88rem;}
div[data-testid="stMetric"] {background:#F7FAFC; border:1px solid #D7E4EC; padding:1rem; border-radius:14px;}
</style>
<div class="hero"><h1>ResMap</h1><p>From bacterial genome sequence to traceable resistance evidence and experimental priorities</p></div>
""", unsafe_allow_html=True)

st.warning("Research-use prototype. The score is not a clinical susceptibility prediction and does not replace standardized AST/MIC testing, expert review or treatment guidance.")

st.markdown("### What the customer sees")
j1,j2,j3 = st.columns(3)
j1.markdown("<div class='journey'><b>1 · Upload</b><br><br>Provide an annotated genome and optional MIC measurements. Sequence-only files are clearly identified.</div>", unsafe_allow_html=True)
j2.markdown("<div class='journey'><b>2 · Understand</b><br><br>Separate obvious resistance genes from hidden supporting mechanisms and important biological context.</div>", unsafe_allow_html=True)
j3.markdown("<div class='journey'><b>3 · Decide</b><br><br>Receive a traceable evidence score, uncertainty statement and priorities for phenotypic validation.</div>", unsafe_allow_html=True)

APP_DIR = Path(__file__).resolve().parent.parent
NCBI_DIR = APP_DIR / "example_data" / "ncbi"
DEMO_OPTIONS = {
    "KPC-positive K. pneumoniae — public NCBI genome": "kp18",
    "KPC-positive E. coli — public NCBI genome": "mncre44",
    "Hidden mechanism: AmpC + altered porin — published case": "ec01",
    "Upload my own genome": "upload",
}

with st.sidebar:
    st.header("Investor demo")
    demo_label = st.selectbox("Choose a customer case", list(DEMO_OPTIONS), index=0)
    demo = DEMO_OPTIONS[demo_label]
    st.header("1 · Genome input")
    uploaded = st.file_uploader("Annotated GenBank preferred; FASTA accepted", type=["gb", "gbk", "gbff", "genbank", "fasta", "fa", "fna"], disabled=demo != "upload")
    st.caption("FASTA contains sequence but no gene annotations. This prototype will not invent gene calls from sequence alone.")
    st.header("2 · Project context")
    demo_context = {
        "kp18": ("KP18-238", "Klebsiella pneumoniae"),
        "mncre44": ("MNCRE44", "Escherichia coli"),
        "ec01": ("EC01", "Escherichia coli"),
        "upload": ("Research isolate 01", "Klebsiella pneumoniae / Escherichia coli"),
    }[demo]
    isolate_id = st.text_input("Isolate ID", demo_context[0])
    organism = st.text_input("Organism", demo_context[1])
    objective = st.text_area("Research objective", "Investigate genomic evidence associated with carbapenem non-susceptibility.")

if demo == "ec01":
    mic_seed = [
        {"antibiotic":"Ertapenem","mic_value":4.0,"unit":"mg/L","method":"Broth microdilution","guideline":"CLSI","version":"2019","interpretation":"R","replicates":1,"source_partner":"Published EC01 case","test_date":None,"notes":">4 mg/L in publication"},
        {"antibiotic":"Imipenem","mic_value":16.0,"unit":"mg/L","method":"Broth microdilution","guideline":"CLSI","version":"2019","interpretation":"R","replicates":1,"source_partner":"Published EC01 case","test_date":None,"notes":">16 mg/L in publication"},
        {"antibiotic":"Meropenem","mic_value":8.0,"unit":"mg/L","method":"Broth microdilution","guideline":"CLSI","version":"2019","interpretation":"R","replicates":1,"source_partner":"Published EC01 case","test_date":None,"notes":"Published numeric MIC"},
    ]
else:
    mic_seed = [{"antibiotic":"Meropenem","mic_value":None,"unit":"mg/L","method":"Broth microdilution","guideline":"EUCAST","version":"","interpretation":"","replicates":1,"source_partner":"Partner / customer","test_date":None,"notes":"Phenotype label requested"}]
default_mic = pd.DataFrame(mic_seed)
st.subheader("Labelled MIC data")
st.caption("Partner/customer phenotype labels remain distinct from genomic evidence and can later support calibration.")
mic_df = st.data_editor(default_mic, num_rows="dynamic", use_container_width=True, key=f"mic_{demo}", column_config={
    "mic_value": st.column_config.NumberColumn("MIC value", min_value=0.0, format="%.4g"),
    "interpretation": st.column_config.SelectboxColumn("S / I / R", options=["", "S", "I", "R"]),
    "test_date": st.column_config.DateColumn("Test date", min_value=date(2000,1,1)),
    "replicates": st.column_config.NumberColumn("Replicates", min_value=1, step=1),
})
mic_rows = mic_df.where(pd.notnull(mic_df), None).to_dict("records")

def load_ncbi_records(names):
    chunks = []
    for name in names:
        path = NCBI_DIR / name
        if not path.exists():
            raise FileNotFoundError(f"Missing demo file: {path.name}")
        chunks.append(path.read_bytes())
    return parse_genome(b"\n".join(chunks), "combined.gbff")

if demo == "kp18":
    try:
        findings, meta = load_ncbi_records(["NZ_CP082014.1.gbff", "NZ_CP082015.1.gbff"])
        meta.update({"source":"NCBI RefSeq annotation", "accessions":"NZ_CP082014.1; NZ_CP082015.1", "case":"Chromosome plus KPC-2 plasmid"})
    except Exception as exc:
        st.error(f"Could not load the packaged NCBI demo: {exc}"); st.stop()
elif demo == "mncre44":
    try:
        findings, meta = load_ncbi_records(["CP010876.1.gbff", "CP010881.1.gbff"])
        meta.update({"source":"NCBI", "accessions":"CP010876.1; CP010881.1", "case":"Chromosome plus resistance plasmid"})
    except Exception as exc:
        st.error(f"Could not load the packaged NCBI demo: {exc}"); st.stop()
elif demo == "ec01":
    findings = [
        Finding("CMY", "Resistance", "Supporting / hidden", "blaCMY-2", "plasmid-mediated AmpC beta-lactamase CMY-2", "literature case", None, None, 2.2, "AmpC alone may not explain carbapenem resistance; interpret with permeability and MIC."),
        Finding("ompC", "Permeability", "Supporting / hidden", "ompC", "altered outer membrane porin C", "literature case", None, None, 1.0, "Published EC01 sequence comparison reported a 12-bp deletion, 12-bp insertion and multiple substitutions."),
        Finding("gyrA", "Resistance", "Context", "gyrA", "S83L and D87N", "literature case", None, None, 0, "Fluoroquinolone-resistance context; not used in the carbapenem score."),
        Finding("parC", "Resistance", "Context", "parC", "S80I", "literature case", None, None, 0, "Fluoroquinolone-resistance context; not used in the carbapenem score."),
    ]
    meta = {"format":"Curated published case", "annotated":True, "records":1, "bases":"not publicly deposited as a complete genome", "source":"Larkin et al., IDCases 2020", "accessions":"No complete EC01 accession reported", "case":"Carbapenemase-negative, blaCMY-2 plus altered ompC", "message":"Literature-derived demonstration. Findings are not claimed as a direct re-analysis of a public complete EC01 genome."}
elif uploaded:
    try:
        findings, meta = parse_genome(uploaded.getvalue(), uploaded.name)
    except Exception as exc:
        st.error(f"Could not parse this file: {exc}")
        st.stop()
else:
    findings, meta = [], {"format":"—", "annotated":False, "records":0, "bases":0, "message":"Upload a genome to begin."}

score = score_findings(findings, mic_rows)
cols = st.columns(4)
cols[0].metric("Evidence score", f"{score['score']} / 100", score["band"])
cols[1].metric("Annotation status", "Annotated" if meta.get("annotated") else "Sequence only / none")
cols[2].metric("Detected findings", len(findings))
cols[3].metric("Labelled MIC rows", len([r for r in mic_rows if r.get("mic_value") is not None]))

obvious = sorted({f.feature for f in findings if f.evidence_tier == "Obvious"})
supporting = sorted({f.feature for f in findings if f.evidence_tier == "Supporting / hidden"})
context_flags = sorted({f.feature for f in findings if f.category == "Iron / uptake"})
st.markdown("### Decision brief")
d1,d2,d3 = st.columns(3)
d1.markdown(f"<div class='journey'><b>Obvious resistance evidence</b><br><br>{', '.join(obvious) if obvious else 'No high-confidence carbapenemase annotation detected.'}</div>", unsafe_allow_html=True)
d2.markdown(f"<div class='journey'><b>Supporting or hidden evidence</b><br><br>{', '.join(supporting) if supporting else 'No validated supporting mechanism identified from the available annotation.'}</div>", unsafe_allow_html=True)
priority = "Confirm labelled MIC and review genotype–phenotype agreement."
if obvious:
    priority = "Confirm MIC, allele and mobile context; compare the compound response across an informative isolate panel."
elif score["synergy_ampc_porin"]:
    priority = "Validate AmpC expression and porin function; repeat carbapenem MIC under standardized conditions."
d3.markdown(f"<div class='journey'><b>Recommended next experiment</b><br><br>{priority}</div>", unsafe_allow_html=True)

gauge = go.Figure(go.Indicator(mode="gauge+number", value=score["score"], number={"suffix":" / 100"}, gauge={"axis":{"range":[0,100]},"bar":{"color":"#F28C28"},"steps":[{"range":[0,25],"color":"#DCEAF5"},{"range":[25,50],"color":"#F9E6A8"},{"range":[50,75],"color":"#F6C55C"},{"range":[75,100],"color":"#E8992E"}]}))
gauge.update_layout(height=270, margin=dict(l=25,r=25,t=25,b=5), paper_bgcolor="#FFFDF7", font={"color":"#12314A"})

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Evidence overview", "Resistance mechanisms", "Iron & uptake", "MIC labels", "Impact scenario"])
with tab1:
    left, right = st.columns([1,1.5])
    left.plotly_chart(gauge, use_container_width=True)
    with right:
        st.markdown(f"<div class='callout'><b>File status:</b> {meta.get('message')}</div>", unsafe_allow_html=True)
        st.write({k:v for k,v in meta.items() if k != "message"})
        st.markdown("**How the score was produced**")
        st.write(score["method"])
        if score["synergy_ampc_porin"]: st.info("AmpC + disrupted porin synergy was triggered.")
        if score["synergy_esbl_porin"]: st.info("ESBL + disrupted porin synergy was triggered.")
        st.json(score["mechanisms"], expanded=False)
with tab2:
    resistance = [x for x in findings_as_dicts(findings) if x["category"] in {"Resistance","Permeability","Efflux","Regulation"}]
    st.dataframe(pd.DataFrame(resistance), use_container_width=True, hide_index=True)
    st.caption("Efflux components or intact porins are contextual findings; expression, disruptive mutations and phenotype determine interpretation.")
with tab3:
    context = [x for x in findings_as_dicts(findings) if x["category"] in {"Iron / uptake","Mobile element"}]
    if context:
        context_df = pd.DataFrame(context)
        summary_df = context_df.groupby(["category","feature","interpretation"], as_index=False).size().sort_values(["category","size"], ascending=[True,False])
        st.dataframe(summary_df.rename(columns={"size":"annotations"}), use_container_width=True, hide_index=True)
        with st.expander("Browse every genomic location"):
            st.dataframe(context_df, use_container_width=True, hide_index=True)
    else:
        st.info("No iron/uptake or mobile-element annotations were identified in the available record.")
    st.caption("These features may inform isolate prioritisation, virulence context, nutrient acquisition and experimental design; they do not directly prove carbapenem resistance.")
with tab4:
    st.dataframe(mic_df, use_container_width=True, hide_index=True)
    st.info("Recommended minimum metadata: antibiotic, numeric MIC, unit, AST method, guideline and version, S/I/R interpretation, replicates, test date and data owner.")
with tab5:
    st.markdown("#### Scenario calculator — modeled, not observed savings")
    c1,c2,c3 = st.columns(3)
    cases = c1.number_input("Affected cases / investigations", 1, 10000, 20)
    days = c2.number_input("Avoidable delay per case", 0.0, 30.0, 2.0, .5)
    daily_cost = c3.number_input("Cost per delay day (€)", 0.0, 10000.0, 700.0, 50.0)
    reducible = st.slider("Share plausibly reduced by the workflow", 0, 100, 25) / 100
    gross = cases * days * daily_cost
    st.metric("Illustrative avoidable cost", f"€{gross*reducible:,.0f}", f"from €{gross:,.0f} modeled exposure")
    st.caption("Benchmark context: published studies associate delayed/inadequate therapy with additional length of stay and costs. This calculator does not establish ResMap causality or clinical benefit.")

report = {"project":{"isolate_id":isolate_id,"organism":organism,"objective":objective},"file":meta,"score":score,"findings":findings_as_dicts(findings),"labelled_mic":mic_rows,"limitations":["Research use only","Uncalibrated evidence score","Phenotypic validation required","Sequence-only FASTA is not gene-annotated"]}
st.download_button("Download traceable JSON report", json.dumps(report, indent=2, default=str), file_name="resmap_report.json", mime="application/json", type="primary")
