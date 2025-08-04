import streamlit as st
import pandas as pd
from pricing_calculator import lclpricing, build_port_lookup
import streamlit.components.v1 as components
from datetime import date
from streamlit_option_menu import option_menu
from io import BytesIO
import os

EXCEL_FILE_PATH = "Data/LCL Pricing Navexel2 2.xlsx"
VALID_EMAIL = "preeti.patil@navexel.com"
VALID_PASSWORD = "N@v3xC3l!4567%"

port_lookup = build_port_lookup(EXCEL_FILE_PATH)

# ------------------ Streamlit UI ------------------
st.set_page_config(page_title="LCL Rate Finder", layout="wide")
st.title("📦 LCL Pricing Lookup")

# ------------------ Session Setup ------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "previous_tab" not in st.session_state:
    st.session_state.previous_tab = "📦 Rate Finder"

selected_tab = option_menu(
    menu_title=None,
    options=["📦 Rate Finder", "📁 Upload & Download"],
    icons=["box", "cloud-upload"],
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "#d4d5d7"},
        "icon": {"color": "black", "font-size": "16px"},
        "nav-link": {
            "font-size": "16px",
            "text-align": "center",
            "--hover-color": "#eee",
        },
        "nav-link-selected": {"background-color": "#050E90"},
    },
)

# ------------------ Reset auth on tab switch ------------------
if selected_tab != st.session_state.previous_tab and selected_tab == "📁 Upload & Download":
    st.session_state.authenticated = False
st.session_state.previous_tab = selected_tab

if selected_tab == "📦 Rate Finder":
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
            if target_rate != of_value:
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
            else:
                message = ""

            # 👉 Show conditional info for BL just below OF info
            if bl_value not in (0.0, "", None) and not pd.isna(bl_value):
                if target_bl != bl_value:
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

# ------------------ Tab 2: Upload & Download ------------------
elif selected_tab == "📁 Upload & Download":

    if not st.session_state.authenticated:
        st.subheader("🔐 Login Required")
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            login = st.form_submit_button("🔐 Login")

        if login:

            if email == VALID_EMAIL and password == VALID_PASSWORD:
                st.session_state.authenticated = True
                st.success("✅ Logged in successfully!")
                st.rerun()
            else:
                st.error("❌ Invalid credentials.")
    else:
        st.subheader("📁 Upload & Download Panel")

        # Logout Button
        if st.button("🚪 Logout"):
            st.session_state.authenticated = False
            st.rerun()

        # Upload/Download Option Menu
        action = option_menu(
            menu_title=None,
            options=["⬇️ Download Excel", "⬆️ Upload Pricing (coming soon)"],
            icons=["download", "upload"],
            orientation="horizontal",
            styles={
                "container": {"padding": "0!important", "background-color": "#d4d5d7"},
                "icon": {"color": "black", "font-size": "14px"},
                "nav-link": {
                    "font-size": "14px",
                    "text-align": "center",
                    "--hover-color": "#eee",
                },
                "nav-link-selected": {"background-color": "#00050a"},
            },
        )

        # Download logic
        if action == "⬇️ Download Excel":
            try:
                if os.path.exists(EXCEL_FILE_PATH):
                    with pd.ExcelFile(EXCEL_FILE_PATH) as xls:
                        all_sheets = {sheet_name: xls.parse(sheet_name) for sheet_name in xls.sheet_names}

                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        for sheet_name, df in all_sheets.items():
                            df.to_excel(writer, sheet_name=sheet_name, index=False)
                    output.seek(0)

                    st.download_button(
                        label="📥 Download Full Excel File",
                        data=output,
                        file_name="LCL_Pricing_Full.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.error("❌ Excel file not found at path.")
            except Exception as e:
                st.error(f"⚠️ Error during download: {e}")

        elif action == "⬆️ Upload Pricing (coming soon)":
            st.info("⏳ Upload functionality will be available in a future update.")


