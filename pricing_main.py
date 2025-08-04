import streamlit as st
import pandas as pd
from pricing_calculator import lclpricing, build_port_lookup
import streamlit.components.v1 as components
from datetime import date

# Load port lookup
port_lookup = build_port_lookup(r"Data/LCL Pricing Navexel2 2.xlsx")

# ------------------ Streamlit UI ------------------
st.set_page_config(page_title="LCL Rate Finder", layout="wide")
st.title("📦 LCL Pricing Lookup")

with st.form("rate_form"):
    port_options = sorted(port_lookup.keys())
    origin_input = st.selectbox("Origin Port", options=port_options, index=port_options.index("Nhava Sheva") if "Nhava Sheva" in port_options else 0)
    destination_input = st.selectbox("Destination Port", options=port_options, index=port_options.index("Ho Chi Minh") if "Ho Chi Minh" in port_options else 1)
    transhipment_input = st.selectbox("Routing (Optional)", options=["Direct"] + port_options, index=0)
    submitted = st.form_submit_button("🔍 Get Rates")

# ------------------ Handle Submission ------------------
if "result_dfs" not in st.session_state:
    st.session_state.result_dfs = None

if submitted:
    def resolve_port(code_or_name):
        return port_lookup.get(code_or_name.strip(), None)

    origin = resolve_port(origin_input)
    destination = resolve_port(destination_input)
    transhipment = resolve_port(transhipment_input) if transhipment_input != "Direct" else "Direct"

    if not origin or not destination:
        st.error("❌ Please enter valid Origin and Destination ports.")
    else:
        st.session_state.result_dfs = lclpricing(origin, destination, transhipment)
        st.session_state.origin = origin
        st.session_state.destination = destination
        st.session_state.transhipment = transhipment

# ------------------ Results ------------------
if st.session_state.result_dfs:
    result_dfs = st.session_state.result_dfs
    transhipment_input = st.session_state.transhipment

    if not result_dfs or all(isinstance(v, pd.DataFrame) and v.empty for v in result_dfs.values()):
        st.warning("⚠️ No matching rates found.")
    else:
        of_value = float(result_dfs.get("OF", 0) or 0)
        col1, col2 = st.columns(2)

        with col1:
            target_rate = st.number_input("Target OF Rate (Per W/M):", value=of_value, step=1.0, format="%.2f", key="target_of_rate")
            st.markdown(f"### 🚢 Ocean Freight (Per W/M) : ${target_rate:.2f}")

        if transhipment_input == "Direct":
            bl_value = float(result_dfs.get("BL", 0) or 0)
            limit_value = float(result_dfs.get("Limit", 0) or 0)
        else:
            bl_value = 0.0
            limit_value = 0.0

        calculated = of_value - limit_value

        with col2:
            if bl_value not in (0.0, "", None) and not pd.isna(bl_value):
                target_bl = st.number_input("Target OF Rate (Per BL):", value=bl_value, step=1.0, format="%.2f", key="target_of_bl")
                st.markdown(f"### 🚢 Ocean Freight (Per BL) : ${target_bl:.2f}")

        # Show tables
        def show_table(title, df):
            if not df.empty:
                st.markdown(f"### {title}")
                st.data_editor(df, use_container_width=True, hide_index=True, disabled=True)
                return df
            return None

        dc_df = show_table("💰 Destination Charges (Charge-wise)", result_dfs.get("DC", pd.DataFrame()))
        dc_allin_df = show_table("💼 Destination Charges (All-in)", result_dfs.get("DC (All in Rate)", pd.DataFrame()))

        dc2_df = show_table("💰 Destination Charges (Charge-wise)", result_dfs.get("DC 2nd Leg", pd.DataFrame()))
        dc2_allin_df = show_table("💼 Destination Charges (All-in)", result_dfs.get("DC 2nd Leg(All in Rate)", pd.DataFrame()))


        # 👉 Show conditional info just below All-in table & include in HTML summary
        diff = round(abs(calculated - target_rate), 2)
        if target_rate > calculated:
            if not diff == 0.0:
                message = f"💡 Reduction in Destination Charges (Per W/M): **${diff}**"
                st.info(message)
            else:
                message = ""
        elif target_rate < calculated:
            if not diff == 0.0:
                message = f"💡 Additional Destination Charges (Per W/M): **${diff}**"
                
                st.info(message)
            else:
                message = ""
        else:
            message = ""

        # 👉 Show conditional info for BL just below OF info
        if bl_value not in (0.0, "", None) and not pd.isna(bl_value):
            bl_diff = round(abs(bl_value - target_bl), 2)
            if target_bl > bl_value:
                if bl_diff != 0.0:
                    bl_message = f"💡 Reduction in Destination Charges (Per BL): **${bl_diff}**"
                    st.info(bl_message)
                else:
                    bl_message = ""
            elif target_bl < bl_value:
                if bl_diff != 0.0:
                    bl_message = f"💡 Additional Destination Charges (Per BL): **${bl_diff}**"
                    st.info(bl_message)
                else:
                    bl_message = ""
            else:
                bl_message = ""



        agent_df = show_table("🧾 Agent", result_dfs.get("Agent", pd.DataFrame()))

        # ------------------ Validity + Copy Section ------------------
        col1, col2 = st.columns([2, 1])
        with col1:
            valid_upto = st.date_input("Valid Upto", value=date.today())
            st.session_state.valid_upto = valid_upto.strftime("%d-%m-%Y")

        # ------------------ HTML Summary + Copy ------------------

        # Convert DataFrame to styled HTML table
        def df_to_html_table(df, title):
            return f"<h4>{title}</h4>" + df.to_html(index=False, border=1, escape=False)

        # Build HTML parts of the summary
        summary_parts = [
            "<h3>LCL Pricing Summary</h3>",
            f"<p><b>Origin:</b> {origin_input}</p>",
            f"<p><b>Destination:</b> {destination_input}</p>",
            f"<p><b>Routing:</b> {transhipment_input}</p>",
            f"<p><b>Valid To:</b> {st.session_state.valid_upto}</p>",
            f"<p><b>Ocean Freight (Per W/M):</b> ${target_rate:.2f}</p>",
        ]

        # Optional: Show Per BL if transhipment is Direct
        if transhipment_input == "Direct" and "target_of_bl" in st.session_state:
            summary_parts.append(f"<p><b>Ocean Freight (Per BL):</b> ${st.session_state.target_of_bl:.2f}</p>")

        # Append tables up to before Agent Details
        for df, label in [
            (dc_df, "Destination Charges (Charge-wise)"),
            (dc_allin_df, "Destination Charges (All-in)"),
            (dc2_df, "Destination Charges (Charge-wise 2nd Leg)"),
            (dc2_allin_df, "Destination Charges (All-in 2nd Leg)")
        ]:
            if df is not None and not df.empty:
                summary_parts.append(df_to_html_table(df, label))

        # Insert messages before Agent Details
        if message:
            summary_parts.append(f"<p><b>{message}</b></p>")
        if bl_value not in (0.0, "", None) and not pd.isna(bl_value):
            summary_parts.append(f"<p><b>{bl_message}</b></p>")

        # Append Agent Details table at the end
        if agent_df is not None and not agent_df.empty:
            summary_parts.append(df_to_html_table(agent_df, "Agent Details"))


        # Combine into one div with ID for clipboard
        full_html = "<div id='copyArea'>" + "".join(summary_parts) + "</div>"

        # Display in UI
        with col2:
            components.html(full_html, height=500, scrolling=True)

