#!/usr/bin/env python3
"""
Streamlit Dashboard for HR Tech Lead Generation System
Beautiful visualization and management interface
"""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database import DatabaseService
from src.export_service import ExportService
from src.constants import SIGNAL_TYPES

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="HR Tech Lead Generator Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state
if "db_service" not in st.session_state:
    st.session_state.db_service = DatabaseService()

if "export_service" not in st.session_state:
    st.session_state.export_service = ExportService()


def main():
    """Main dashboard application"""
    st.title("🚀 HR Tech Lead Generation Dashboard")
    st.markdown("---")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        database_url = st.text_input(
            "Database URL",
            value="sqlite:///opportunities.db",
            help="SQLite: sqlite:///file.db\nPostgreSQL: postgresql://user:pass@host/db",
        )
        
        if st.button("🔄 Reload Database"):
            st.session_state.db_service = DatabaseService(database_url)
            st.success("Database reloaded!")
            st.rerun()

        st.markdown("---")
        st.header("📊 Quick Stats")
        stats = st.session_state.db_service.get_statistics()
        st.metric("Total Opportunities", stats["total_opportunities"])
        st.metric("Contacted", f"{stats['contacted_count']} ({stats['contacted_percentage']}%)")
        st.metric("Avg Relevance", f"{stats['avg_relevance']:.2f}")

    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📋 Opportunities", "📈 Analytics", "⚙️ Settings"])

    with tab1:
        show_overview(st.session_state.db_service)

    with tab2:
        show_opportunities(st.session_state.db_service, st.session_state.export_service)

    with tab3:
        show_analytics(st.session_state.db_service)

    with tab4:
        show_settings(st.session_state.db_service)


def show_overview(db_service: DatabaseService):
    """Show overview dashboard"""
    st.header("📊 Overview Dashboard")

    stats = db_service.get_statistics()

    if stats["total_opportunities"] == 0:
        st.warning("No opportunities in database. Run the lead generator first!")
        return

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Opportunities", stats["total_opportunities"])
    with col2:
        st.metric("Average Relevance", f"{stats['avg_relevance']:.3f}")
    with col3:
        st.metric("Contacted", f"{stats['contacted_count']} ({stats['contacted_percentage']}%)")
    with col4:
        st.metric("Email Validated", stats["email_validated_count"])

    st.markdown("---")

    # Distribution by signal
    if PLOTLY_AVAILABLE and stats["by_signal"]:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📈 Distribution by Signal Type")
            signal_data = {
                "Signal Type": [
                    SIGNAL_TYPES.get(sid, f"Signal {sid}") for sid in stats["by_signal"].keys()
                ],
                "Count": list(stats["by_signal"].values()),
            }
            df_signals = pd.DataFrame(signal_data)

            fig = px.bar(
                df_signals,
                x="Signal Type",
                y="Count",
                color="Count",
                color_continuous_scale="Blues",
                title="Opportunities by Signal Type",
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("🥧 Signal Type Pie Chart")
            fig_pie = px.pie(
                df_signals,
                values="Count",
                names="Signal Type",
                title="Opportunities Distribution",
            )
            fig_pie.update_layout(height=400)
            st.plotly_chart(fig_pie, use_container_width=True)

    # Recent opportunities table
    st.subheader("🆕 Recent Opportunities")
    recent_opps = db_service.get_opportunities(limit=10, order_by="created_at", descending=True)
    if recent_opps:
        df_recent = pd.DataFrame([
            {
                "Company": opp.company,
                "Person": opp.person,
                "Email": opp.email,
                "Relevance": f"{opp.relevance_score:.2f}",
                "Signal": SIGNAL_TYPES.get(opp.signal_type, f"Signal {opp.signal_type}"),
                "Created": opp.created_at.strftime("%Y-%m-%d %H:%M") if hasattr(opp.created_at, 'strftime') else str(opp.created_at),
            }
            for opp in recent_opps
        ])
        st.dataframe(df_recent, use_container_width=True, hide_index=True)
    else:
        st.info("No recent opportunities")


def show_opportunities(db_service: DatabaseService, export_service: ExportService):
    """Show opportunities management"""
    st.header("📋 Opportunities Management")

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        signal_filter = st.selectbox(
            "Filter by Signal",
            options=["All"] + list(SIGNAL_TYPES.values()),
        )
    with col2:
        min_relevance = st.slider("Min Relevance Score", 0.0, 1.0, 0.0, 0.1)
    with col3:
        limit = st.number_input("Limit Results", min_value=10, max_value=1000, value=100, step=10)

    # Get opportunities
    signal_id = None
    if signal_filter != "All":
        signal_id = next(
            (sid for sid, name in SIGNAL_TYPES.items() if name == signal_filter),
            None,
        )

    opportunities = db_service.get_opportunities(
        signal_type=signal_id,
        min_relevance=min_relevance,
        limit=limit,
    )

    st.info(f"Found {len(opportunities)} opportunities")

    # Export buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📥 Export to CSV"):
            opps_list = [opp.to_opportunity() for opp in opportunities]
            filepath = export_service.export_to_csv(opps_list)
            if filepath:
                st.success(f"✅ Exported to {filepath}")
    with col2:
        if st.button("📊 Export to Excel"):
            opps_list = [opp.to_opportunity() for opp in opportunities]
            filepath = export_service.export_to_excel(opps_list)
            if filepath:
                st.success(f"✅ Exported to {filepath}")
    with col3:
        if st.button("📈 Export Summary Report"):
            opps_list = [opp.to_opportunity() for opp in opportunities]
            # Get metrics (simplified)
            metrics = {
                "total_opportunities": len(opps_list),
                "average_relevance_score": sum(opp.relevance_score for opp in opps_list) / len(opps_list) if opps_list else 0,
            }
            filepath = export_service.export_summary_report(opps_list, metrics)
            if filepath:
                st.success(f"✅ Exported to {filepath}")

    st.markdown("---")

    # Opportunities table
    if opportunities:
        df = pd.DataFrame([
            {
                "ID": opp.id,
                "Company": opp.company,
                "Person": opp.person,
                "Email": opp.email,
                "Relevance": f"{opp.relevance_score:.3f}",
                "Signal": SIGNAL_TYPES.get(opp.signal_type, f"Signal {opp.signal_type}"),
                "Contacted": "✅" if opp.contacted else "❌",
                "Created": opp.created_at.strftime("%Y-%m-%d") if hasattr(opp.created_at, 'strftime') else str(opp.created_at),
            }
            for opp in opportunities
        ])

        st.dataframe(df, use_container_width=True, hide_index=True)

        # Opportunity details
        st.subheader("🔍 Opportunity Details")
        selected_id = st.selectbox(
            "Select Opportunity ID",
            options=[opp.id for opp in opportunities],
        )

        if selected_id:
            opp = db_service.get_opportunity_by_id(selected_id)
            if opp:
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Company:** {opp.company}")
                    st.write(f"**Person:** {opp.person}")
                    st.write(f"**Email:** {opp.email}")
                    st.write(f"**URL:** {opp.url}")
                with col2:
                    st.write(f"**Relevance Score:** {opp.relevance_score:.3f}")
                    st.write(f"**Signal Type:** {SIGNAL_TYPES.get(opp.signal_type, 'Unknown')}")
                    st.write(f"**Source:** {opp.source}")
                    st.write(f"**Contacted:** {'Yes' if opp.contacted else 'No'}")

                st.text_area("Content", opp.content[:500], height=200)

                # Actions
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Mark as Contacted"):
                        db_service.mark_contacted(selected_id)
                        st.success("Marked as contacted!")
                        st.rerun()
                with col2:
                    if st.button("🗑️ Delete"):
                        if db_service.delete_opportunity(selected_id):
                            st.success("Deleted!")
                            st.rerun()
    else:
        st.info("No opportunities found with current filters")


def show_analytics(db_service: DatabaseService):
    """Show analytics and insights"""
    st.header("📈 Analytics & Insights")

    stats = db_service.get_statistics()

    if stats["total_opportunities"] == 0:
        st.warning("No data available for analytics")
        return

    # Relevance score distribution
    if PLOTLY_AVAILABLE:
        opportunities = db_service.get_opportunities(limit=1000)
        if opportunities:
            relevance_scores = [opp.relevance_score for opp in opportunities]

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("📊 Relevance Score Distribution")
                fig = px.histogram(
                    x=relevance_scores,
                    nbins=20,
                    title="Distribution of Relevance Scores",
                    labels={"x": "Relevance Score", "y": "Count"},
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.subheader("📈 Relevance Score Over Time")
                # Group by date
                dates = []
                scores = []
                for opp in opportunities:
                    if hasattr(opp.created_at, 'date'):
                        dates.append(opp.created_at.date())
                        scores.append(opp.relevance_score)

                if dates:
                    df_time = pd.DataFrame({"Date": dates, "Score": scores})
                    df_time = df_time.groupby("Date")["Score"].mean().reset_index()
                    fig = px.line(
                        df_time,
                        x="Date",
                        y="Score",
                        title="Average Relevance Score Over Time",
                    )
                    st.plotly_chart(fig, use_container_width=True)

    # Top companies
    st.subheader("🏢 Top Companies")
    opportunities = db_service.get_opportunities(limit=1000)
    if opportunities:
        company_counts = {}
        for opp in opportunities:
            company_counts[opp.company] = company_counts.get(opp.company, 0) + 1

        top_companies = sorted(company_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        df_companies = pd.DataFrame(top_companies, columns=["Company", "Opportunities"])
        st.dataframe(df_companies, use_container_width=True, hide_index=True)


def show_settings(db_service: DatabaseService):
    """Show settings and maintenance"""
    st.header("⚙️ Settings & Maintenance")

    st.subheader("🗑️ Database Maintenance")

    col1, col2 = st.columns(2)

    with col1:
        days = st.number_input("Delete opportunities older than (days)", min_value=30, max_value=365, value=90)
        if st.button("🗑️ Clean Old Opportunities"):
            count = db_service.clear_old_opportunities(days=days)
            st.success(f"Deleted {count} old opportunities!")

    with col2:
        st.info("💡 Database Statistics")
        stats = db_service.get_statistics()
        st.json(stats)

    st.markdown("---")
    st.subheader("📥 Export All Data")
    
    all_opps = db_service.get_opportunities(limit=10000)
    if all_opps:
        opps_list = [opp.to_opportunity() for opp in all_opps]
        export_service = ExportService()
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Export All to CSV"):
                filepath = export_service.export_to_csv(opps_list)
                st.success(f"✅ Exported to {filepath}")
        with col2:
            if st.button("📊 Export All to Excel"):
                filepath = export_service.export_to_excel(opps_list)
                st.success(f"✅ Exported to {filepath}")


if __name__ == "__main__":
    main()

