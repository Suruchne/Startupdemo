from __future__ import annotations

import itertools
import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from brand import apply_brand, hero

apply_brand()
hero("Experimental design", "Translate isolates, MIC evidence and laboratory capacity into a transparent screening DoE")

st.info("Planning prototype only. Final inoculum, medium, incubation, concentrations, QC strains and endpoints must follow the partner laboratory’s validated SOP and current CLSI/EUCAST method.")

st.markdown("## 1 · Customer inputs")
c1,c2,c3,c4 = st.columns(4)
design_mode = c1.selectbox("Design objective", ["Confirm MIC across isolates", "Mechanism screen · factorial DoE"])
n_isolates = c2.number_input("Number of isolates", 1, 96, 4)
n_compounds = c3.number_input("Number of compounds", 1, 8, 1)
max_plates = c4.number_input("Available 96-well plates", 1, 100, 4)

r1,r2,r3,r4 = st.columns(4)
technical_reps = r1.selectbox("Technical replicates", [1,2,3], index=1)
biological_reps = r2.selectbox("Independent biological runs", [1,2,3], index=0)
n_concentrations = r3.slider("Concentration points", 4, 10, 8)
guideline = r4.selectbox("Method framework", ["EUCAST / ISO", "CLSI", "Research SOP · not standardized"])

st.markdown("### Available resources")
q1,q2,q3,q4,q5 = st.columns(5)
plate_reader = q1.checkbox("Plate reader", True)
cfu_capability = q2.checkbox("Viable-count capability")
automation = q3.checkbox("Liquid handling automation")
iron_media = q4.checkbox("Iron-controlled media")
partner_lab = q5.checkbox("Partner microbiology lab", True)

ids = [f"ISO-{i+1:02d}" for i in range(int(n_isolates))]
mic_template = pd.DataFrame({"isolate_id":ids,"mechanism_group":["Unknown"]*len(ids),"baseline_mic_mg_L":[None]*len(ids),"mic_method":[guideline]*len(ids),"include":[True]*len(ids)})
st.caption("Paste available labelled MICs. Missing values remain explicit and the design uses relative-to-MIC concentrations.")
mic_df = st.data_editor(mic_template, num_rows="fixed", use_container_width=True, key=f"mic_design_{n_isolates}_{guideline}", column_config={"baseline_mic_mg_L":st.column_config.NumberColumn("Baseline MIC, mg/L",min_value=0.0,format="%.4g"),"include":st.column_config.CheckboxColumn("Include")})
selected = mic_df[mic_df["include"] == True].copy()
if selected.empty:
    st.error("Select at least one isolate in the MIC table to build an experimental design.")
    st.stop()

factor_iron = factor_modulator = False
if design_mode.startswith("Mechanism"):
    st.markdown("### DoE factors")
    f1,f2,f3 = st.columns(3)
    f1.checkbox("Compound exposure: 0.5×, 1× and 2× MIC", value=True, disabled=True)
    factor_iron = f2.checkbox("Iron state: standard vs limited", value=iron_media)
    factor_modulator = f3.checkbox("Mechanism modulator: absent vs present")

def mic_design():
    multipliers = [8,4,2,1,.5,.25,.125,.0625,.03125,.015625][:n_concentrations]
    rows=[]; plate_no=0
    rows_per_plate=8
    for bio in range(1,biological_reps+1):
        for compound in range(1,int(n_compounds)+1):
            assignments=[]
            for _, rec in selected.iterrows():
                for tech in range(1,technical_reps+1): assignments.append((rec,tech))
            for offset in range(0,len(assignments),rows_per_plate):
                plate_no += 1
                for ridx,(rec,tech) in enumerate(assignments[offset:offset+rows_per_plate]):
                    row=chr(65+ridx); mic=rec["baseline_mic_mg_L"]
                    for col,mult in enumerate(multipliers,1):
                        actual=None if pd.isna(mic) else float(mic)*mult
                        rows.append({"plate":plate_no,"well":f"{row}{col}","isolate":rec["isolate_id"],"mechanism":rec["mechanism_group"],"compound":f"Compound {compound}","biological_run":bio,"technical_replicate":tech,"condition":f"{mult:g}× MIC","concentration_mg_L":actual,"measurement":"Growth / no growth; OD" if plate_reader else "Visual growth / no growth"})
                    rows.append({"plate":plate_no,"well":f"{row}11","isolate":rec["isolate_id"],"mechanism":rec["mechanism_group"],"compound":f"Compound {compound}","biological_run":bio,"technical_replicate":tech,"condition":"Growth control","concentration_mg_L":0,"measurement":"Growth acceptance"})
                    rows.append({"plate":plate_no,"well":f"{row}12","isolate":"None","mechanism":"Control","compound":f"Compound {compound}","biological_run":bio,"technical_replicate":tech,"condition":"Sterility / optical blank","concentration_mg_L":None,"measurement":"Background"})
    return pd.DataFrame(rows),plate_no

def factorial_design():
    drug_levels=["0.5× MIC","1× MIC","2× MIC"]
    iron_levels=["Standard","Iron-limited"] if factor_iron else ["Standard"]
    mod_levels=["Absent","Present"] if factor_modulator else ["Absent"]
    combinations=list(itertools.product(drug_levels,iron_levels,mod_levels))
    experimental=[]
    for bio in range(1,biological_reps+1):
        for compound in range(1,int(n_compounds)+1):
            for _,rec in selected.iterrows():
                for combo in combinations:
                    for tech in range(1,technical_reps+1):
                        experimental.append({"isolate":rec["isolate_id"],"mechanism":rec["mechanism_group"],"compound":f"Compound {compound}","biological_run":bio,"technical_replicate":tech,"drug_level":combo[0],"iron_state":combo[1],"modulator":combo[2],"condition":" · ".join(combo),"measurement":"OD kinetics" if plate_reader else "Endpoint growth"})
    rows=[]
    for idx,run in enumerate(experimental):
        plate=idx//88+1; pos=idx%88; row=chr(65+pos//11); col=pos%11+1
        rows.append({"plate":plate,"well":f"{row}{col}",**run})
    plates=max(1,math.ceil(len(experimental)/88))
    for plate in range(1,plates+1):
        controls=[("A12","Growth control"),("B12","Vehicle control"),("C12","Compound blank"),("D12","Medium sterility"),("E12","Mechanism-positive control"),("F12","Mechanism-negative control"),("G12","Inoculum verification"),("H12","Reserved repeat")]
        for well,condition in controls:
            rows.append({"plate":plate,"well":well,"isolate":"Control","mechanism":"Control","compound":"—","biological_run":"—","technical_replicate":"—","drug_level":"—","iron_state":"—","modulator":"—","condition":condition,"measurement":"QC"})
    return pd.DataFrame(rows),plates

design_df,plates = mic_design() if design_mode.startswith("Confirm") else factorial_design()

st.markdown("## 2 · ResMap design")
m1,m2,m3,m4=st.columns(4)
m1.metric("Required plates",plates)
m2.metric("Planned wells",len(design_df))
m3.metric("Included isolates",len(selected))
m4.metric("Capacity status","Fits" if plates<=max_plates else "Over capacity",f"{max_plates} available")
if plates>max_plates:
    st.error("The requested design exceeds current capacity. Reduce isolates, compounds or replication, or add plates. ResMap does not silently remove controls.")
elif len(selected)==0:
    st.error("Select at least one isolate.")
else:
    st.success("The design fits the declared plate capacity. Controls and provenance remain explicit in the run sheet.")

plate_choice=st.selectbox("Preview plate",list(range(1,plates+1)))
preview=design_df[design_df["plate"]==plate_choice]
grid=[["Empty" for _ in range(12)] for _ in range(8)]
for _,rec in preview.iterrows():
    row=ord(rec["well"][0])-65; col=int(rec["well"][1:])-1
    grid[row][col]=rec["condition"]
categories={v:i for i,v in enumerate(sorted({x for row in grid for x in row}))}
z=[[categories[x] for x in row] for row in grid]
fig=go.Figure(go.Heatmap(z=z,text=grid,texttemplate="%{text}",hovertemplate="Well %{y}%{x}<br>%{text}<extra></extra>",colorscale=[[0,"#E8F4F2"],[.5,"#F5C45E"],[1,"#F28C28"]],showscale=False,x=list(range(1,13)),y=list("ABCDEFGH"),xgap=4,ygap=4))
fig.update_yaxes(autorange="reversed",title="Plate row");fig.update_xaxes(title="Plate column",side="top");fig.update_layout(height=620,margin=dict(l=40,r=20,t=60,b=30),font=dict(family="Trebuchet MS",color="#123B3A"),plot_bgcolor="white")
st.plotly_chart(fig,use_container_width=True)

st.markdown("### Measurements and analysis plan")
measurements=["Primary: standardized growth/no-growth endpoint and MIC or relative response","Replicate agreement and predefined QC acceptance","Genotype–phenotype concordance and outlier flagging"]
if plate_reader: measurements.append("OD kinetics: lag time, maximum growth, growth rate and area under the curve")
if cfu_capability: measurements.append("Orthogonal viable counts for selected discordant or high-value conditions")
if factor_iron: measurements.append("Main effect of iron state and interaction with compound exposure")
if factor_modulator: measurements.append("Main effect of mechanism modulator and interaction with compound exposure")
for item in measurements: st.write("• "+item)

st.download_button("Download complete run sheet",design_df.to_csv(index=False).encode(),"resmap_experimental_design.csv","text/csv",type="primary")
with st.expander("Browse run sheet"):
    st.dataframe(design_df,use_container_width=True,hide_index=True)
