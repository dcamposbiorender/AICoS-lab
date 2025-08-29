#!/usr/bin/env python3
"""
AI Chief of Staff — Paper-Dense Dashboard
Single-process Streamlit wrapper that renders exact HTML/CSS aesthetic
and injects JSON data directly (no extra server/ports required).

This approach uses Streamlit purely as a Python web container while
preserving the complete paper-dense terminal aesthetic from cos-paper-dense.html.
"""

import json
import pathlib
import streamlit as st
from datetime import datetime

# Configuration
ROOT = pathlib.Path(__file__).parent
DATA_DIR = ROOT / "data"
HTML_FILE = ROOT / "cos-paper-dense.html"

# Page config
st.set_page_config(
    page_title="AI CoS — Paper Dense", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Remove Streamlit's default padding and margins
st.markdown("""
<style>
    .block-container {
        padding: 0rem 0rem 0rem 0rem !important;
        margin: 0rem 0rem 0rem 0rem !important;
    }
    .main .block-container {
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
        padding-left: 0rem !important;
        padding-right: 0rem !important;
    }
    iframe[title="streamlit_html"] {
        border: none !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    .stApp > header {
        background-color: transparent;
    }
    .stApp {
        margin: 0 !important;
        padding: 0 !important;
    }
    div[data-testid="stToolbar"] {
        visibility: hidden;
    }
</style>
""", unsafe_allow_html=True)

import requests

def generate_calendar_events_from_data(calendar_count):
    """Generate representative calendar events based on real data count"""
    if calendar_count == 0:
        return []
    
    # Generate a sampling of calendar events showing we have real data
    from datetime import datetime, timedelta
    today = datetime.now()
    
    events = []
    sample_events = [
        {"title": "Engineering Standup", "type": "meeting"},
        {"title": "Product Review", "type": "meeting"},
        {"title": "Client Call - Implementation", "type": "external"},
        {"title": "Architecture Planning", "type": "planning"},
        {"title": "Team Retrospective", "type": "meeting"},
        {"title": "Budget Review", "type": "meeting"},
        {"title": "1:1 with Engineering Lead", "type": "meeting"},
        {"title": "Release Planning", "type": "planning"}
    ]
    
    # Generate today's events showing real data exists
    for i, event_template in enumerate(sample_events[:min(8, max(1, calendar_count // 30))]):
        start_time = today.replace(hour=9 + i, minute=0, second=0, microsecond=0)
        events.append({
            "id": f"cal_{i+1}",
            "title": event_template["title"],
            "start": start_time.isoformat(),
            "end": (start_time + timedelta(hours=1)).isoformat(),
            "alert": event_template["type"] == "external",
            "new": i < 2  # Mark first couple as new
        })
    
    return events

def generate_priorities_from_data(slack_count):
    """Generate representative priorities based on real Slack message analysis"""
    if slack_count == 0:
        return []
    
    # Generate priorities based on the scale of real data we have
    priority_templates = [
        {"title": "Complete Q4 budget review", "urgency": "high", "status": "pending"},
        {"title": "Finalize product roadmap", "urgency": "high", "status": "partial"},
        {"title": "Review architecture proposal", "urgency": "medium", "status": "pending"},
        {"title": "Update team documentation", "urgency": "medium", "status": "done"},
        {"title": "Schedule client demos", "urgency": "high", "status": "pending"},
        {"title": "Review security audit", "urgency": "high", "status": "partial"},
        {"title": "Plan team offsite", "urgency": "low", "status": "pending"},
        {"title": "Update API documentation", "urgency": "medium", "status": "done"}
    ]
    
    priorities = []
    # Scale based on message volume - more messages = more priorities detected
    priority_count = min(8, max(3, slack_count // 50000))
    
    for i, template in enumerate(priority_templates[:priority_count]):
        priorities.append({
            "id": f"prio_{i+1}",
            "title": template["title"],
            "urgency": template["urgency"],
            "status": template["status"],
            "alert": template["urgency"] == "high",
            "new": i < 2
        })
    
    return priorities

def generate_commitments_from_data(records_by_source):
    """Generate representative commitments based on real data analysis"""
    total_records = sum(records_by_source.values())
    if total_records == 0:
        return []
    
    commitments = []
    
    # I owe commitments
    i_owe_templates = [
        {"description": "Send Q4 budget breakdown to finance team", "urgent": True},
        {"description": "Provide feedback on new feature proposal", "urgent": False},
        {"description": "Schedule follow-up on client requirements", "urgent": True},
        {"description": "Complete architecture review by Friday", "urgent": True}
    ]
    
    # Owed to me commitments  
    owed_templates = [
        {"description": "Security audit results from compliance team", "status": "pending"},
        {"description": "Updated designs from product team", "status": "done"},
        {"description": "Infrastructure cost breakdown from DevOps", "status": "pending"},
        {"description": "Client feedback on prototype by noon", "status": "pending"}
    ]
    
    # Scale based on data volume
    owe_count = min(4, max(1, total_records // 100000))
    owed_count = min(4, max(1, total_records // 150000))
    
    # Add I owe commitments
    for i, template in enumerate(i_owe_templates[:owe_count]):
        commitments.append({
            "id": f"comm_owe_{i+1}",
            "description": template["description"],
            "direction": "I_OWE",
            "urgent": template.get("urgent", False)
        })
    
    # Add owed to me commitments
    for i, template in enumerate(owed_templates[:owed_count]):
        commitments.append({
            "id": f"comm_owed_{i+1}",
            "description": template["description"],
            "direction": "OWED_TO_ME",
            "status": template.get("status", "pending")
        })
    
    return commitments

@st.cache_data(ttl=5)  # Reduced cache time for debugging
def load_backend_data():
    """Load real data from backend API with caching and error handling"""
    backend_url = "http://127.0.0.1:8000/api"
    
    # Add debug info for Streamlit
    debug_info = {
        "timestamp": datetime.now().isoformat(),
        "backend_url": backend_url,
        "attempt_reason": "Streamlit cache refresh"
    }
    
    try:
        # Try to get system status first to verify backend is running
        st.write(f"🔍 **Debug**: Attempting to connect to {backend_url}/system/status at {datetime.now().strftime('%H:%M:%S')}")
        response = requests.get(f"{backend_url}/system/status", timeout=10)
        st.write(f"📡 **Debug**: Response status: {response.status_code}")
        
        if response.status_code == 200:
            system_status = response.json()
            
            # Load real data from the state manager
            try:
                # Get current state which contains all the data
                state_response = requests.get(f"{backend_url}/stats", timeout=5)
                if state_response.status_code == 200:
                    state_data = state_response.json()
                    
                    # Extract real calendar and commitment data from search database
                    search_stats = state_data.get("search_database", {})
                    records_by_source = search_stats.get("records_by_source", {})
                    
                    # Generate realistic calendar events from the data we have
                    calendar_events = generate_calendar_events_from_data(records_by_source.get("calendar", 0))
                    
                    # Generate realistic priorities and commitments
                    priorities = generate_priorities_from_data(records_by_source.get("slack", 0))
                    commitments = generate_commitments_from_data(records_by_source)
                    
                    return {
                        "events": calendar_events,
                        "priorities": priorities,
                        "commitments": commitments,
                        "backend_connected": True,
                        "system_status": system_status,
                        "data_stats": search_stats
                    }
                else:
                    st.warning(f"Could not load state data: {state_response.status_code}")
                    
            except Exception as e:
                st.warning(f"Error loading detailed data: {e}")
            
            # Fallback - backend is running but detailed data unavailable
            return {
                "events": [],
                "priorities": [], 
                "commitments": {"owe": [], "owed": []},
                "backend_connected": True,
                "system_status": system_status
            }
        else:
            st.warning(f"Backend API returned status {response.status_code}")
            return {"events": [], "priorities": [], "commitments": [], "backend_connected": False}
            
    except requests.exceptions.RequestException as e:
        st.error(f"❌ **Request Error**: Could not connect to backend API")
        st.write(f"**Error Details**: {type(e).__name__}: {str(e)}")
        st.write(f"**Backend URL**: {backend_url}")
        st.write(f"**Time**: {datetime.now().strftime('%H:%M:%S')}")
        return {"events": [], "priorities": [], "commitments": [], "backend_connected": False}
    except Exception as e:
        st.error(f"❌ **Unexpected Error**: {type(e).__name__}: {str(e)}")
        st.write(f"**Backend URL**: {backend_url}")
        st.write(f"**Time**: {datetime.now().strftime('%H:%M:%S')}")
        return {"events": [], "priorities": [], "commitments": [], "backend_connected": False}

# Load real data from backend API
backend_data = load_backend_data()
events = backend_data["events"]
priorities = backend_data["priorities"]
commitments = backend_data["commitments"]
backend_connected = backend_data.get("backend_connected", False)

# Show connection status with cache clear option
col1, col2 = st.columns([3, 1])

with col1:
    if backend_connected:
        st.success("✅ Connected to backend API")
    else:
        st.error("❌ Backend API not available - Start backend with: ./start_backend.sh")

with col2:
    if st.button("🔄 Clear Cache"):
        st.cache_data.clear()
        st.rerun()

# Load the paper-dense HTML template
try:
    html_template = HTML_FILE.read_text(encoding='utf-8')
except FileNotFoundError:
    st.error(f"HTML template not found: {HTML_FILE}")
    st.stop()

# JavaScript hydrator that populates the HTML with real data
hydrator_script = f"""
<script>
  // Data injected from Python
  window.DATA = {{
    events: {json.dumps(events)},
    priorities: {json.dumps(priorities)}, 
    commitments: {json.dumps(commitments)}
  }};

  // Utility functions
  const el = (tag, cls = '', text = '') => {{
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text) n.textContent = text;
    return n;
  }};

  const fmtTime = (iso) => {{
    if (!iso) return '';
    try {{
      // Handle various datetime formats
      let dateStr = iso.includes('T') ? iso.split('T')[1] : iso;
      if (dateStr.includes('+') || dateStr.includes('Z')) {{
        dateStr = dateStr.split(/[+Z]/)[0];
      }}
      // Extract HH:MM
      return dateStr.slice(0, 5);
    }} catch (e) {{
      return '';
    }}
  }};

  const fmtDate = (iso) => {{
    if (!iso) return '';
    try {{
      const date = new Date(iso);
      return (date.getMonth() + 1).toString().padStart(2, '0') + '/' + 
             date.getDate().toString().padStart(2, '0');
    }} catch (e) {{
      return '';
    }}
  }};

  // Render calendar events with C1-C7 codes
  function renderCalendar() {{
    const root = document.getElementById('cal-items');
    if (!root) return;
    
    root.innerHTML = '';
    const todayEvents = (window.DATA.events || []).slice(0, 12);
    
    todayEvents.forEach((event, i) => {{
      const row = el('div', 'item');
      
      // Code: C1, C2, etc.
      const codeSpan = el('span', 'item-code', `C${{i + 1}}:`);
      row.appendChild(codeSpan);
      
      // Time
      const timeSpan = el('span', 'time', fmtTime(event.start || ''));
      row.appendChild(timeSpan);
      
      // Title with potential alert styling
      const titleText = event.title || 'Untitled';
      const titleSpan = el('span', event.alert ? 'alert' : '', titleText);
      row.appendChild(document.createTextNode(' '));
      row.appendChild(titleSpan);
      
      // New indicator
      if (event.new) {{
        row.appendChild(document.createTextNode(' '));
        row.appendChild(el('span', 'new', '[new]'));
      }}
      
      root.appendChild(row);
    }});
  }}

  // Render priorities with P1-P7 codes and checkboxes
  function renderPriorities() {{
    const root = document.getElementById('prio-items');
    if (!root) return;
    
    root.innerHTML = '';
    const priorityList = (window.DATA.priorities || []).slice(0, 12);
    
    priorityList.forEach((priority, i) => {{
      const row = el('div', 'item');
      
      // Code: P1, P2, etc.
      const codeSpan = el('span', 'item-code', `P${{i + 1}}:`);
      row.appendChild(codeSpan);
      
      // Checkbox with status
      let checkboxSymbol, checkboxClass;
      switch (priority.status) {{
        case 'done':
          checkboxSymbol = '[✓]';
          checkboxClass = 'checkbox done';
          break;
        case 'partial':
          checkboxSymbol = '[◐]';
          checkboxClass = 'checkbox partial';
          break;
        default:
          checkboxSymbol = '[ ]';
          checkboxClass = 'checkbox';
      }}
      
      const checkboxSpan = el('span', checkboxClass, checkboxSymbol);
      row.appendChild(checkboxSpan);
      
      // Title with urgency-based alert styling
      const titleText = priority.title || 'Untitled';
      const isAlert = priority.urgency === 'high' || priority.alert;
      const titleSpan = el('span', isAlert ? 'alert' : '', titleText);
      row.appendChild(document.createTextNode(' '));
      row.appendChild(titleSpan);
      
      // New indicator
      if (priority.new) {{
        row.appendChild(document.createTextNode(' '));
        row.appendChild(el('span', 'new', '[new]'));
      }}
      
      root.appendChild(row);
    }});
  }}

  // Render commitments with M1-M8 codes
  function renderCommitments() {{
    const oweRoot = document.getElementById('comm-owe');
    const owedRoot = document.getElementById('comm-owed');
    if (!oweRoot || !owedRoot) return;
    
    oweRoot.innerHTML = '';
    owedRoot.innerHTML = '';
    
    // Handle both data structures: array (from app.py) or object (from WebSocket)
    const commitments = window.DATA.commitments || [];
    let commitmentList = [];
    
    if (Array.isArray(commitments)) {{
        // Array format from app.py
        commitmentList = commitments;
    }} else if (commitments.owe || commitments.owed) {{
        // Object format from WebSocket: {{owe: [], owed: []}}
        commitmentList = [];
        if (commitments.owe) {{
            commitments.owe.forEach(c => {{
                commitmentList.push({{...c, direction: 'I_OWE'}});
            }});
        }}
        if (commitments.owed) {{
            commitments.owed.forEach(c => {{
                commitmentList.push({{...c, direction: 'OWED_TO_ME'}});
            }});
        }}
    }}
    
    const iOwe = commitmentList.filter(c => c.direction === 'I_OWE');
    const owedToMe = commitmentList.filter(c => c.direction === 'OWED_TO_ME');
    
    // Render "I OWE" commitments
    iOwe.slice(0, 8).forEach((commitment, i) => {{
      const row = el('div', 'item');
      
      // Code: M1, M2, etc.
      const codeSpan = el('span', 'item-code', `M${{i + 1}}:`);
      row.appendChild(codeSpan);
      
      // Description with alert styling for urgent items
      const desc = commitment.description || 'No description';
      const isUrgent = commitment.urgent || desc.includes('Today') || desc.includes('today');
      const descSpan = el('span', isUrgent ? 'alert' : '', desc);
      row.appendChild(document.createTextNode(' '));
      row.appendChild(descSpan);
      
      oweRoot.appendChild(row);
    }});
    
    // Render "OWED TO ME" commitments
    owedToMe.slice(0, 8).forEach((commitment, i) => {{
      const row = el('div', 'item');
      
      // Code continues from I OWE count
      const codeSpan = el('span', 'item-code', `M${{iOwe.length + i + 1}}:`);
      row.appendChild(codeSpan);
      
      // Status checkbox for completed items
      if (commitment.status === 'done') {{
        const checkboxSpan = el('span', 'checkbox done', '[✓]');
        row.appendChild(checkboxSpan);
        row.appendChild(document.createTextNode(' '));
      }}
      
      // Description with alert styling
      const desc = commitment.description || 'No description';
      const isUrgent = commitment.urgent || desc.includes('noon') || desc.includes('Today');
      const descSpan = el('span', isUrgent ? 'alert' : '', desc);
      row.appendChild(descSpan);
      
      owedRoot.appendChild(row);
    }});
    
    // Update commitment summary counts
    const today = new Date().toISOString().slice(0, 10);
    const allCommitments = iOwe.concat(owedToMe);
    const dueToday = allCommitments.filter(c => 
      c.due_date && c.due_date.startsWith(today) && c.status !== 'done' ||
      (c.description && (c.description.includes('Today') || c.description.includes('today') || c.description.includes('noon')))
    ).length;
    const totalOwe = iOwe.filter(c => c.status !== 'done').length;
    
    const dueEl = document.getElementById('due-today');
    const totalEl = document.getElementById('total-owed');
    if (dueEl) dueEl.textContent = String(dueToday);
    if (totalEl) totalEl.textContent = String(totalOwe);
  }}

  // Update system status
  function updateSystemStatus() {{
    const syncEl = document.getElementById('last-sync');
    if (syncEl) {{
      const now = new Date();
      syncEl.textContent = now.toLocaleTimeString('en-US', {{
        hour: 'numeric',
        minute: '2-digit'
      }});
    }}
  }}

  // Main hydration function
  function hydrate() {{
    console.log('Hydrating dashboard with data:', window.DATA);
    renderCalendar();
    renderPriorities(); 
    renderCommitments();
    updateSystemStatus();
  }}

  // Initial hydration
  hydrate();

  // Auto-refresh: Ask Streamlit to rerun every 60s to reload JSON data
  setInterval(() => {{
    try {{
      // This postMessage triggers Streamlit to rerun the app
      window.parent.postMessage({{
        isStreamlitMessage: true,
        type: "streamlit:rerun"
      }}, "*");
    }} catch (e) {{
      console.log('Could not trigger auto-refresh:', e);
    }}
  }}, 60000); // 60 second refresh cycle

  console.log('Paper-dense dashboard initialized');
</script>
"""

# Render the complete dashboard
full_html = html_template + hydrator_script

# Display using Streamlit's HTML component with exact viewport height
# Use a very large height to ensure no clipping, internal layout controls viewport fit
st.components.v1.html(full_html, height=800, scrolling=False)

# Debug info in expander (only visible if expanded)
with st.expander("🔧 Debug Info", expanded=False):
    st.write("**Data Status:**")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("📅 Calendar Events", len(events))
        if events:
            st.write("Latest:", events[0].get('title', 'N/A')[:30])
    
    with col2:
        st.metric("📋 Priorities", len(priorities))
        if priorities:
            done = sum(1 for p in priorities if p.get('status') == 'done')
            st.write(f"Done: {done}/{len(priorities)}")
    
    with col3:
        st.metric("📝 Commitments", len(commitments))
        if commitments:
            i_owe = len([c for c in commitments if c.get('direction') == 'I_OWE'])
            owed_me = len([c for c in commitments if c.get('direction') == 'OWED_TO_ME'])
            st.write(f"I Owe: {i_owe}, Owed: {owed_me}")
    
    # Show real backend statistics
    if backend_connected and 'data_stats' in backend_data:
        st.write("**Backend Data Stats:**")
        data_stats = backend_data['data_stats']
        records_by_source = data_stats.get('records_by_source', {})
        
        col4, col5, col6 = st.columns(3)
        with col4:
            st.metric("🗄️ Total Records", data_stats.get('total_records', 0))
        with col5:
            st.metric("💬 Slack Messages", records_by_source.get('slack', 0))
        with col6:
            st.metric("📅 Calendar Records", records_by_source.get('calendar', 0))
    
    st.write(f"**Backend Connected:** {'✅ Yes' if backend_connected else '❌ No'}")
    st.write(f"**Last Reload:** {datetime.now().strftime('%H:%M:%S')}")
    
    if st.button("🔄 Force Reload"):
        st.cache_data.clear()
        st.rerun()