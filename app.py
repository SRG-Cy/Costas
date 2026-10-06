"""Costas - what will it cost to live in Ireland? A calm, sourced estimate for newcomers.

Run:  streamlit run app.py
"""
import pandas as pd
import streamlit as st

import ai
import costs
from costs import BEDROOM_OPTIONS, Choices

st.set_page_config(page_title="Costas: living costs in Ireland", page_icon="🍀", layout="centered")


CSS = """
<style>
.block-container {max-width: 860px; padding-top: 2.5rem;}
header[data-testid="stHeader"] {background: transparent;}
.stButton > button, .stDownloadButton > button {border-radius: 999px; padding: .55rem 1.5rem; font-weight: 600;}
.stButton > button {white-space: nowrap;}
[data-testid="stColumn"] .stButton > button {width: 100%;}
.stButton > button[kind="primary"] {color: #03110b;}
.hero h1 {font-size: clamp(2.6rem, 7vw, 4.4rem); line-height: 1.02; letter-spacing: -0.03em; margin: .4rem 0 1rem;}
.hero .accent {background: linear-gradient(90deg, #52d3a2, #cfe9a8); -webkit-background-clip: text; color: transparent;}
.hero p {font-size: 1.15rem; color: #92a49b; max-width: 36rem;}
.pill {display: inline-block; border: 1px solid #1b2c25; border-radius: 999px; padding: .2rem .8rem;
       font-size: .75rem; letter-spacing: .12em; text-transform: uppercase; color: #92a49b;}
.sample {background: #0c1814; border: 1px solid #1b2c25; border-radius: 22px; padding: 1.2rem 1.4rem; margin: 1.6rem 0; max-width: 28rem;}
.sample .k {color: #92a49b; font-size: .8rem;}
.sample .big {font-size: 1.9rem; font-weight: 700; color: #52d3a2;}
.cards {display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; margin: 1rem 0;}
.card {border-radius: 22px; padding: 1.1rem 1.3rem; border: 1px solid #1b2c25; background: #0c1814;}
.card .k {color: #92a49b; font-size: .85rem;}
.card .v {font-size: 2rem; font-weight: 700; letter-spacing: -0.02em;}
.card.total {background: #0f2c24; border-color: #1f5a46;}
.card.total .v {color: #52d3a2;}
.card.oneoff {background: #2a2312; border-color: #4a3d18;}
.card.oneoff .v {color: #efc65c;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def eur(x: float) -> str:
    return f"€{x:,.0f}"


@st.cache_data
def counties():
    return costs.counties()




STEPS = ["Welcome", "Where", "Home", "Extras", "Result"]
DEFAULTS = {"county": "Dublin", "in_city": False, "housing": "room", "bedrooms": "One bed",
            "room_type": "single", "dwelling": "house", "ensuite": False, "include_gym": False, "needs_irp": False}

if "step" not in st.session_state:
    st.session_state.step = 0
if "answers" not in st.session_state:
    st.session_state.answers = dict(DEFAULTS)
A = st.session_state.answers


def go(step: int):
    st.session_state.step = step


def nav(back: int | None, next_: int | None, next_label: str = "Next"):
    cols = st.columns([1, 2, 3])
    if back is not None:
        cols[0].button("Back", on_click=go, args=(back,), key=f"back{back}")
    if next_ is not None:
        cols[1].button(next_label, type="primary", on_click=go, args=(next_,), key=f"next{next_}")


step = st.session_state.step
if step > 0:
    st.progress(step / (len(STEPS) - 1), text=f"Step {step} of {len(STEPS) - 1}: {STEPS[step]}")

if step == 0:
    st.markdown(
        '<div class="hero"><span class="pill">Hacktoberfest 2026 · Ireland</span>'
        '<h1>Moving to Ireland?<br><span class="accent">Know the cost first.</span></h1>'
        '<p>Answer three quick questions. Get a monthly estimate and the cash you need on arrival, '
        'built from official data. Every number shows its source and date.</p>'
        '<div class="sample"><div class="k">Example · room in Galway City</div>'
        '<div class="big">about €2,000 a month</div>'
        '<div class="k">plus one-off move-in cash. Yours depends on your answers.</div></div></div>',
        unsafe_allow_html=True)
    st.button("Start", type="primary", on_click=go, args=(1,))
    if ai.available():
        st.markdown("**Or just describe your situation**")
        text = st.text_area("Describe your situation", label_visibility="collapsed", max_chars=800,
                            placeholder="e.g. I'm a student from India moving to Galway next month and want a room in a shared house")
        st.caption("The text is sent to an AI service (Google) to fill in the form. Do not include personal details. "
                   "You can review and change every answer before you see an estimate.")
        if st.button("Fill the form for me") and text.strip():
            with st.spinner("Reading your description..."):
                found = ai.parse_situation(text)
            if found:
                A.update(found)
                st.session_state.prefilled = True
                go(1)
                st.rerun()
            else:
                st.warning("I couldn't read that. Try again, or press Start and answer the questions.")
                if ai.LAST_ERROR:
                    st.caption(f"Technical detail: {ai.LAST_ERROR}")

elif step == 1:
    st.header("Where will you live?")
    if st.session_state.pop("prefilled", False):
        st.success("I filled this in from your description. Check each step and change anything that's wrong.")
    cs = counties()
    A["county"] = st.selectbox("County", cs, index=cs.index(A["county"]))
    city = costs.city_option(A["county"])
    if city:
        opts = [city, f"Elsewhere in {A['county']}"]
        where = st.radio(f"Are you living in {city} or elsewhere in County {A['county']}?", opts,
                         index=0 if A["in_city"] else 1)
        A["in_city"] = where == city
    else:
        A["in_city"] = False
    nav(0, 2)

elif step == 2:
    st.header("What kind of home?")
    labels = ["A room in a shared house", "My own place (flat or house)"]
    pick = st.radio("Housing", labels, index=0 if A["housing"] == "room" else 1)
    A["housing"] = "room" if pick == labels[0] else "own_place"
    if A["housing"] == "own_place":
        A["bedrooms"] = st.selectbox("Bedrooms", BEDROOM_OPTIONS, index=BEDROOM_OPTIONS.index(A["bedrooms"]))
    else:
        c1, c2, c3 = st.columns(3)
        A["room_type"] = c1.radio("Room", ["single", "double"], index=["single", "double"].index(A["room_type"]))
        A["dwelling"] = c2.radio("In a", ["house", "apartment"], index=["house", "apartment"].index(A["dwelling"]))
        A["ensuite"] = c3.radio("Ensuite?", ["No", "Yes"], index=1 if A["ensuite"] else 0) == "Yes"
    nav(1, 3)

elif step == 3:
    st.header("Anything extra?")
    A["include_gym"] = st.checkbox("Gym membership (rough estimate, no source yet)", value=A["include_gym"])
    A["needs_irp"] = st.checkbox(
        "I am from outside the EU, EEA, UK and Switzerland and will stay more than 90 days (IRP registration, €300)",
        value=A["needs_irp"])
    nav(2, 4, "See my estimate")

else:
    county, in_city, housing = A["county"], A["in_city"], A["housing"]
    bedrooms, room_type, dwelling, ensuite = A["bedrooms"], A["room_type"], A["dwelling"], A["ensuite"]
    city = costs.city_option(county)
    est = costs.estimate(Choices(county=county, housing=housing, in_city=in_city, bedrooms=bedrooms,
                                 room_type=room_type, dwelling=dwelling, ensuite=ensuite,
                                 include_gym=A["include_gym"], needs_irp=A["needs_irp"]))
    st.header("Your estimate")
    place = city if (in_city and city) else county
    st.caption(f"{place} · {est.housing_label}")
    one_off = ""
    if est.housing:
        one_off = f'<div class="card oneoff"><div class="k">One-off cash on arrival</div><div class="v">{eur(est.arrival_total)}</div></div>'
    st.markdown(
        '<div class="cards">'
        f'<div class="card"><div class="k">Housing / month</div><div class="v">{eur(est.housing)}</div></div>'
        f'<div class="card"><div class="k">Everyday essentials / month</div><div class="v">{eur(est.essentials)}</div></div>'
        f'<div class="card total"><div class="k">Total per month</div><div class="v">{eur(est.total)}</div></div>'
        f'{one_off}</div>', unsafe_allow_html=True)
    if est.housing:
        extra = f" + IRP registration {eur(est.irp)}" if est.irp else ""
        st.caption(
            f"One-off cash = deposit {eur(est.deposit)} + first month's rent {eur(est.housing)}{extra}. "
            "The RTB caps a standard private-rental deposit and advance rent at one month's rent each. "
            "Student accommodation can differ.")
    st.caption("An estimate, not advice. One-off costs cover deposit, first month and (if selected) IRP only. Visa and permit fees, and setup items, are not included yet.")
    for n in est.notes:
        st.info(n)

    if ai.available():
        with st.expander("Explain this in plain words (AI)"):
            lang = st.selectbox("Language", ai.LANGUAGES)
            if st.button("Explain"):
                with st.spinner("Writing..."):
                    txt = ai.explain(est, place, lang)
                if txt:
                    st.write(txt)
                    st.caption("Written by an AI from the figures above. Check the numbers in the breakdown tab.")
                else:
                    st.warning("The AI explanation wasn't usable, so it's hidden. The figures above are unaffected.")
                    if ai.LAST_ERROR:
                        st.caption(f"Technical detail: {ai.LAST_ERROR}")

    tab_break, tab_time, tab_compare, tab_sources = st.tabs(["Breakdown", "Rent over time", "Compare places", "Sources and limits"])

    with tab_break:
        df = pd.DataFrame([{"Item": l.label, "Per month": eur(l.amount), "Source": l.source,
                            "As of": l.as_of, "Confidence": l.confidence} for l in est.lines])
        st.dataframe(df, hide_index=True, width="stretch")
        chart = pd.DataFrame({"€ per month": [l.amount for l in est.lines]},
                             index=[l.label.split(":")[0].split(" (")[0] for l in est.lines])
        st.bar_chart(chart)

    with tab_time:
        area_bed = bedrooms if housing == "own_place" else "One bed"
        area = city if (in_city and city) else county
        hist = costs.rent_history(area, area_bed)
        if not hist:
            hist = costs.rent_history(county, area_bed)
            area = county
        if housing == "room":
            st.caption("Room-rent history is not loaded yet (one quarter only). For context, here is the "
                       "rent for a whole one-bed home in the same area.")
        if hist:
            st.line_chart(pd.DataFrame(hist, columns=["Half-year", "€ per month"]).set_index("Half-year"))
            st.caption(f"Average monthly rent, {area_bed.lower()}, {area}. Source: RTB Rent Index via CSO (RIH02).")

    with tab_compare:
        if housing == "own_place":
            data = costs.own_place_by_county(bedrooms)
            st.caption(f"Average monthly rent for a {bedrooms.lower()} home, by county, {costs.latest_period()}.")
            st.bar_chart(pd.DataFrame(data, columns=["County", "€ per month"]).set_index("County"))
        else:
            data = costs.rooms_by_market(room_type, dwelling, ensuite)
            st.caption(f"Average listed rent for a {room_type} room in a {dwelling}"
                       f"{' with' if ensuite else ', no'} ensuite, by market, 2026Q1 (Daft.ie).")
            st.bar_chart(pd.DataFrame(data, columns=["Market", "€ per month"]).set_index("Market"))
            st.caption("Markets with too few listings are left out.")

    with tab_sources:
        st.markdown("**What this estimate is**")
        st.markdown(
            "- **Housing:** whole homes use the RTB Rent Index (registered tenancies, half-yearly, latest 2025H2). "
            "Rooms use Daft.ie *listed* (asking) rents from the Q1 2026 rental report.\n"
            "- **Everyday essentials:** the Vincentian MESL budget for a single working-age adult in an urban "
            "area, excluding housing (MESL 2025). It is a national figure, so it does not vary by county, "
            "and it is for someone already settled in Ireland.\n"
            "- **Not included yet:** visa and permit fees, setup items (SIM, bedding), health "
            "insurance, childcare, and anything for couples or families.")
        st.markdown("**Sourced items in the catalogue (for reference, already inside the essentials figure)**")
        cat = pd.DataFrame([{"Item": c["label"], "Low": c["monthly_eur_low"], "High": c["monthly_eur_high"],
                             "Status": c["status"], "Source": c["source_name"], "As of": c["as_of"],
                             "Link": c["source_url"]} for c in costs.catalogue() if c["status"] in ("verified", "estimate")])
        st.dataframe(cat, hide_index=True, width="stretch",
                     column_config={"Link": st.column_config.LinkColumn("Link")})
        st.caption("Items marked *estimate* have no source yet.")

    st.divider()
    st.caption("Built for Hacktoberfest 2026. Data: CSO/RTB, Daft.ie, Vincentian MESL Research Centre, GoMo, Selectra. "
               "Figures change: always check the linked sources.")
    st.button("Start over", on_click=lambda: (st.session_state.update(step=0, answers=dict(DEFAULTS))))
