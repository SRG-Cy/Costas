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


def half_year_to_date(s: str):
    """'2008H1' -> 1 Jan 2008, '2008H2' -> 1 Jul 2008, so charts show years, not codes."""
    return pd.Timestamp(year=int(s[:4]), month=1 if s.endswith("H1") else 7, day=1)


def period_words(s: str) -> str:
    """'2025H2' -> 'the second half of 2025'."""
    return f"the {'first' if s.endswith('H1') else 'second'} half of {s[:4]}"


@st.cache_data
def counties():
    return costs.counties()




STEPS = ["Welcome", "Where", "Home", "About you", "Result"]
DEFAULTS = {"county": "Dublin", "in_city": False, "housing": "room", "bedrooms": "One bed",
            "room_type": "single", "dwelling": "house", "ensuite": False, "include_gym": False, "needs_irp": False, "persona": "student"}

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
if 0 < step < len(STEPS):
    st.progress(step / (len(STEPS) - 1), text=f"Step {step} of {len(STEPS) - 1}: {STEPS[step]}")

if step == 0:
    st.markdown(
        '<div class="hero">'
        '<h1>Moving to Ireland?<br><span class="accent">Know the cost first.</span></h1>'
        '<p>Answer three quick questions. Get a monthly estimate and the cash you need on arrival, '
        'built from official data. Every number comes with its source.</p>'
        '<div class="sample"><div class="k">Example · a student in a room in Galway City</div>'
        '<div class="big">about €1,200 a month</div>'
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
                st.session_state.ai_filled = set(found)
                go(5)
                st.rerun()
            else:
                st.warning("I couldn't read that. Try again, or press Start and answer the questions.")
                if ai.LAST_ERROR:
                    st.caption(f"Technical detail: {ai.LAST_ERROR}")

elif step == 1:
    st.header("Where will you live?")
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
    kinds = ["room", "own_place"]
    A["housing"] = st.radio("What are you looking for?", kinds, horizontal=True,
                            index=kinds.index(A["housing"]),
                            format_func=lambda k: "A room in a shared house" if k == "room" else "My own place (flat or house)")
    with st.container(border=True):
        if A["housing"] == "own_place":
            A["bedrooms"] = st.radio("How many bedrooms?", BEDROOM_OPTIONS, horizontal=True,
                                     index=BEDROOM_OPTIONS.index(A["bedrooms"]))
        else:
            rt = ["single", "double"]
            A["room_type"] = st.radio("Type of room", rt, horizontal=True, index=rt.index(A["room_type"]),
                                      format_func=str.capitalize)
            dw = ["house", "apartment"]
            A["dwelling"] = st.radio("Type of home", dw, horizontal=True, index=dw.index(A["dwelling"]),
                                     format_func=str.capitalize)
            A["ensuite"] = st.radio("Bathroom", [False, True], horizontal=True, index=1 if A["ensuite"] else 0,
                                    format_func=lambda b: "Own ensuite" if b else "Shared bathroom")
    nav(1, 3)

elif step == 3:
    st.header("A little about you")
    personas = ["student", "professional"]
    A["persona"] = st.radio("Are you coming to study or to work?", personas, horizontal=True,
                            index=personas.index(A["persona"]),
                            format_func=lambda p: "To study (student)" if p == "student" else "To work (professional)")
    st.caption("This changes everyday costs such as food, going out, transport and health insurance.")
    A["include_gym"] = st.checkbox("Add a gym membership (rough estimate, no source yet)", value=A["include_gym"])
    A["needs_irp"] = st.checkbox(
        "I am from outside the EU, EEA, UK and Switzerland and will stay more than 90 days (IRP registration, €300)",
        value=A["needs_irp"])
    nav(2, 4, "See my estimate")

elif step == 5:
    st.header("Is this right?")
    st.write("Here is what I understood from your description. Check it, then confirm. "
             "Anything I couldn't tell from your text is marked *assumed*.")
    filled = st.session_state.get("ai_filled", set())

    def val(key: str, text: str) -> str:
        return text if key in filled else f"{text} (assumed)"

    cty = A["county"]
    cc = costs.city_option(cty)
    place_txt = (f"{cc}, Co. {cty}" if A["in_city"] and cc else (f"Elsewhere in Co. {cty}" if cc else f"Co. {cty}"))
    rows = [("Where", val("county", place_txt))]
    if A["housing"] == "room":
        rows.append(("Looking for", val("housing", "A room in a shared house")))
        rows.append(("Room", val("room_type", A["room_type"].capitalize())))
        rows.append(("Home", val("dwelling", A["dwelling"].capitalize())))
        rows.append(("Bathroom", val("ensuite", "Own ensuite" if A["ensuite"] else "Shared bathroom")))
    else:
        rows.append(("Looking for", val("housing", "My own place (flat or house)")))
        rows.append(("Bedrooms", val("bedrooms", A["bedrooms"])))
    rows.append(("Coming to", val("persona", "Study (student)" if A["persona"] == "student" else "Work (professional)")))
    rows.append(("Gym membership", val("include_gym", "Yes" if A["include_gym"] else "No")))
    rows.append(("Needs IRP registration (non-EU)", val("needs_irp", "Yes" if A["needs_irp"] else "No")))
    st.markdown('<div class="cards" style="grid-template-columns:1fr;">' + "".join(
        f'<div class="card" style="display:flex;justify-content:space-between;gap:1rem;padding:.8rem 1.2rem;">'
        f'<span class="k">{k}</span><span style="font-weight:600;text-align:right;">{v}</span></div>'
        for k, v in rows) + '</div>', unsafe_allow_html=True)
    cols = st.columns([2, 2, 2])
    cols[0].button("Confirm and see my estimate", type="primary", on_click=go, args=(4,), key="confirm")
    cols[1].button("Change something", on_click=go, args=(1,), key="change")

else:
    county, in_city, housing = A["county"], A["in_city"], A["housing"]
    bedrooms, room_type, dwelling, ensuite = A["bedrooms"], A["room_type"], A["dwelling"], A["ensuite"]
    city = costs.city_option(county)
    est = costs.estimate(Choices(county=county, housing=housing, in_city=in_city, bedrooms=bedrooms,
                                 room_type=room_type, dwelling=dwelling, ensuite=ensuite,
                                 include_gym=A["include_gym"], needs_irp=A["needs_irp"], persona=A["persona"]))
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
    st.markdown("[Sources](#sources)")
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

    tab_break, tab_time, tab_compare = st.tabs(["Breakdown", "Rent over time", "Compare places"])

    with tab_break:
        df = pd.DataFrame([{"Item": l.label, "Per month": eur(l.amount), "How reliable": l.confidence}
                           for l in est.lines])
        st.dataframe(df, hide_index=True, width="stretch")

    with tab_time:
        area_bed = bedrooms if housing == "own_place" else "One bed"
        area = city if (in_city and city) else county
        hist = costs.rent_history(area, area_bed)
        if not hist:
            hist = costs.rent_history(county, area_bed)
            area = county
        if housing == "room":
            st.caption("We only have one set of room prices, so here is how the rent for a whole "
                       "one-bed home in the same area has changed.")
        if hist:
            frame = pd.DataFrame({"Year": [half_year_to_date(h) for h, _ in hist],
                                  "€ per month": [v for _, v in hist]}).set_index("Year")
            st.line_chart(frame)
            first, last = hist[0][0][:4], hist[-1][0][:4]
            st.caption(f"Average monthly rent for a {area_bed.lower()} home in {area}, {first} to {last}.")

    with tab_compare:
        if housing == "own_place":
            data = costs.own_place_by_county(bedrooms)
            st.caption(f"Average monthly rent for a {bedrooms.lower()} home, by county, in {period_words(costs.latest_period())}.")
            st.bar_chart(pd.DataFrame(data, columns=["County", "€ per month"]).set_index("County"))
        else:
            data = costs.rooms_by_market(room_type, dwelling, ensuite)
            st.caption(f"Average advertised rent for a {room_type} room in a {dwelling}"
                       f"{' with an ensuite' if ensuite else ' with a shared bathroom'}, by area, early 2026.")
            st.bar_chart(pd.DataFrame(data, columns=["Market", "€ per month"]).set_index("Market"))
            st.caption("Areas with too few adverts are left out.")

    with st.expander("What is inside everyday essentials?"):
        who = "a student" if A["persona"] == "student" else "a working professional"
        st.write(f"Typical monthly costs for {who}, by category:")
        basket = pd.DataFrame([{"What": k, "Per month": eur(v), "Note": n} for k, v, n in est.essentials_detail]
                              + [{"What": "Total", "Per month": eur(est.essentials), "Note": ""}])
        st.dataframe(basket, hide_index=True, width="stretch")
        st.caption("These are estimated typical costs, not official statistics. Prices vary around the country, "
                   "and your own habits will move these figures up or down. A whole home uses the average electricity "
                   "bill for a small home and adds broadband; gas and heating are not included yet. Where no figure "
                   "was available (a professional's health insurance) the official minimum-budget share is used.")
        st.markdown(f"**For comparison:** the official minimum budget for a settled adult (MESL) is about "
                    f"{eur(est.mesl_reference)} a month excluding housing. It assumes a permanent household, "
                    "so it runs higher than a typical student budget.")
        st.markdown("**How the official minimum budget splits**")
        st.dataframe(pd.DataFrame([{"What": k, "Per month (about)": eur(v)} for k, v in costs.mesl_breakdown()]),
                     hide_index=True, width="stretch")
        st.caption("The 2025 report gives only the total. This applies the shares of the official 2024 budget "
                   "for a single adult in a city to the 2025 total.")

    # ---------------------------------------------------------------- sources (the "Sources" link jumps here)
    st.divider()
    st.subheader("Sources", anchor="sources")
    cat = {c["item_id"]: c for c in costs.catalogue()}
    room_url = costs.room_source_url()
    st.markdown(
        "- **Rent for a whole home:** RTB Rent Index, published by the CSO "
        f"([table RIH02](https://data.cso.ie/table/RIH02)), latest {period_words(costs.latest_period())}.\n"
        f"- **Rent for a room:** Daft.ie Rental Report, first quarter 2026 ([report]({room_url})). "
        "These are advertised (asking) rents.\n"
        "- **Everyday essentials:** estimated typical monthly costs for a student or a working professional "
        "(not an official statistic), with one gap filled from the official MESL budget. "
        f"[Vincentian MESL 2025]({cat['mesl_single_urban']['source_url']}) is shown for comparison.\n"
        "- **Official minimum budget, split by category (comparison only):** [MESL 2024 budget, single adult, city]"
        "(https://budgeting.ie/wp-content/uploads/2024/08/WA_Core_MESL_U_2024.pdf), shares applied to the 2025 total.\n"
        f"- **Deposit and first month:** [RTB rules]({cat['arrival_deposit']['source_url']}): at most one month's rent each.\n"
        + (f"- **IRP registration fee (€300):** [DkIT]({cat['arrival_registration']['source_url']}). A university page, so check the official fee before you rely on it.\n" if est.irp else "")
        + "- **Not included yet:** visa and permit fees, setup items (SIM, bedding), health insurance, "
        "childcare, and anything for couples or families.")
    ref = [c for c in cat.values() if c["status"] == "verified" and c["source_url"]
           and c["item_id"] not in ("mesl_single_urban", "arrival_deposit")]
    if ref:
        with st.expander("Other prices we checked (for reference)"):
            for c in ref:
                st.markdown(f"- [{c['label']}]({c['source_url']}) ({c['source_name']})")

    st.caption("Figures change. Always check the linked sources.")
    st.button("Start over", on_click=lambda: (st.session_state.update(step=0, answers=dict(DEFAULTS))))
