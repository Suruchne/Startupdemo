import streamlit as st

from brand import apply_brand, hero

apply_brand()
hero("ResMap", "Genome-informed isolate selection and experimental design for antimicrobial research")

st.markdown("## Turn existing genome sequences into better experiments")
st.write("ResMap helps research teams understand bacterial isolates, choose the most informative subset, and design an efficient first experiment. It combines established resistance evidence with permeability, regulation, virulence, iron acquisition, uptake systems, mobile elements and labelled MIC data.")

a,b,c = st.columns(3)
a.markdown('<div class="resmap-card"><b>Antibiotic developers</b><br><br>Select isolates that challenge a new compound across distinct resistance mechanisms, lineages and biological contexts.</div>', unsafe_allow_html=True)
b.markdown('<div class="resmap-card"><b>Compound-testing teams</b><br><br>Move from a long isolate list to a controlled in-vitro activity design with concentrations, comparators and measurements.</div>', unsafe_allow_html=True)
c.markdown('<div class="resmap-card"><b>Infection researchers</b><br><br>Investigate genotype–phenotype discordance and prioritize mechanistic follow-up instead of repeating every possible assay.</div>', unsafe_allow_html=True)

st.markdown("## What ResMap does")
s1,s2,s3,s4 = st.columns(4)
s1.markdown('<div class="resmap-step"><b>1 · Characterise</b><br><br>Organise resistance, porins, efflux, iron uptake, virulence and mobile context.</div>', unsafe_allow_html=True)
s2.markdown('<div class="resmap-step"><b>2 · Prioritise</b><br><br>Rank isolates by the customer’s scientific question and identify informative contrasts.</div>', unsafe_allow_html=True)
s3.markdown('<div class="resmap-step"><b>3 · Design</b><br><br>Convert MICs, isolate count and available resources into a transparent DoE and plate plan.</div>', unsafe_allow_html=True)
s4.markdown('<div class="resmap-step"><b>4 · Learn</b><br><br>Capture labelled MIC and assay results to improve future recommendations.</div>', unsafe_allow_html=True)

st.markdown("## Explore the prototype")
g,e = st.columns(2)
with g:
    st.markdown('<div class="resmap-card"><b>Genome evidence</b><br><br>Browse packaged KPC and hidden-resistance examples or upload an annotated genome. See obvious, supporting and contextual findings.</div>', unsafe_allow_html=True)
    st.page_link("pages/1_Genome_Evidence.py", label="Open genome evidence →", icon="🧬")
with e:
    st.markdown('<div class="resmap-card"><b>Experimental design</b><br><br>Enter MIC values, isolate numbers, replicates and laboratory resources. Receive plate requirements, a balanced design and downloadable run sheet.</div>', unsafe_allow_html=True)
    st.page_link("pages/2_Experimental_Design.py", label="Build an experiment →", icon="🧪")

st.markdown('<div class="resmap-note"><b>Research-use boundary:</b> ResMap supports experimental planning. It does not replace standardized AST, expert microbiological review, clinical breakpoints or treatment decisions.</div>', unsafe_allow_html=True)
