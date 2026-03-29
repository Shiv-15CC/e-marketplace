import streamlit as st
import pandas as pd
import oracledb
import hashlib
import time

st.set_page_config(page_title="E-Marketplace Pro", page_icon="🏛️", layout="wide")

# ─── CUSTOM CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background: #0f0f13; color: #e8e6e3; }
    [data-testid="stSidebar"] { background: #16161d; }
    .stTabs [data-baseweb="tab-list"] { background: #16161d; border-radius: 10px; padding: 4px; }
    .stTabs [data-baseweb="tab"] { color: #888; border-radius: 8px; }
    .stTabs [aria-selected="true"] { background: #e8c86e; color: #0f0f13 !important; font-weight: 700; }
    .stButton > button { background: #e8c86e; color: #0f0f13; border: none; font-weight: 700;
                         border-radius: 8px; transition: all 0.2s; }
    .stButton > button:hover { background: #f0d98a; transform: translateY(-1px); }
    .listing-card { background: #16161d; border: 1px solid #2a2a35; border-radius: 12px;
                    padding: 16px; margin-bottom: 12px; }
    .price-tag { color: #e8c86e; font-size: 1.4rem; font-weight: 800; }
    .sold-badge { background: #3a1a1a; color: #ff6b6b; padding: 2px 10px;
                  border-radius: 20px; font-size: 0.8rem; font-weight: 700; }
    .active-badge { background: #1a3a1a; color: #6bff8a; padding: 2px 10px;
                    border-radius: 20px; font-size: 0.8rem; font-weight: 700; }
    .notif-unread { background: #1e1e2e; border-left: 3px solid #e8c86e;
                    padding: 10px; border-radius: 6px; margin-bottom: 8px; }
    .notif-read { background: #16161d; border-left: 3px solid #333;
                  padding: 10px; border-radius: 6px; margin-bottom: 8px; opacity: 0.6; }
    div[data-testid="stForm"] { background: #16161d; border: 1px solid #2a2a35;
                                  border-radius: 12px; padding: 20px; }
    .stTextInput > div > div > input, .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea { background: #0f0f13 !important; color: #e8e6e3 !important;
                                          border: 1px solid #2a2a35 !important; }
    .stSelectbox > div > div { background: #0f0f13 !important; }
    h1, h2, h3 { color: #e8c86e !important; }
    .stDataFrame { background: #16161d; }
    [data-testid="stMetricValue"] { color: #e8c86e !important; font-size: 2rem !important; }
</style>
""", unsafe_allow_html=True)

# ─── DB CONNECTION ─────────────────────────────────────────────────────────────
def get_connection():
    try:
        conn = oracledb.connect(
            user="system",
            password="shivam15",
            dsn="localhost/XE"   # ← Change to localhost/ORCL if needed
        )
        return conn
    except oracledb.DatabaseError as e:
        st.error(f"❌ DB Connection Failed: {e}")
        return None

def run_query(sql, params=None):
    """Run a SELECT and return a DataFrame."""
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params or [])
        cols = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        return pd.DataFrame(rows, columns=cols)
    except Exception as e:
        st.error(f"Query Error: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def run_dml(sql, params=None):
    """Run INSERT/UPDATE/DELETE. Returns (success, message)."""
    conn = get_connection()
    if not conn:
        return False, "No DB connection"
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params or [])
        conn.commit()
        return True, "OK"
    except oracledb.DatabaseError as e:
        error_obj = e.args[0]
        return False, getattr(error_obj, 'message', str(e))
    finally:
        conn.close()

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# ─── SESSION STATE ─────────────────────────────────────────────────────────────
for key, default in [('user_id', None), ('username', None), ('last_refresh', 0)]:
    if key not in st.session_state:
        st.session_state[key] = default

# ─── AUTO-REFRESH LOGIC ──────────────────────────────────────────────────────
# Refresh every 10 seconds if logged in
AUTO_REFRESH_SEC = 10

# ─── LOGIN / SIGNUP PAGE ──────────────────────────────────────────────────────
if st.session_state['user_id'] is None:
    st.markdown("<h1 style='text-align:center'>🏛️ E-Marketplace Portal</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#888'>Buy • Sell • Connect</p>", unsafe_allow_html=True)
    st.divider()

    col_l, col_m, col_r = st.columns([1, 1.5, 1])
    with col_m:
        tab_login, tab_signup = st.tabs(["🔑 Log In", "✨ Sign Up"])

        with tab_login:
            with st.form("login_form"):
                l_email = st.text_input("Email")
                l_pass  = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Log In", use_container_width=True)
                if submitted:
                    df = run_query(
                        'SELECT USERID, USERNAME FROM USERS WHERE EMAIL = :1 AND PASSWORDHASH = :2',
                        [l_email, hash_password(l_pass)]
                    )
                    if not df.empty:
                        st.session_state['user_id']  = int(df.iloc[0]['USERID'])
                        st.session_state['username'] = df.iloc[0]['USERNAME']
                        st.success("✅ Logged in!")
                        st.rerun()
                    else:
                        st.error("Invalid email or password.")

        with tab_signup:
            with st.form("signup_form"):
                s_user  = st.text_input("Username")
                s_email = st.text_input("Email")
                s_pass  = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Create Account", use_container_width=True)
                if submitted:
                    ok, msg = run_dml(
                        'INSERT INTO USERS (USERID, USERNAME, EMAIL, PASSWORDHASH, REGISTRATIONDATE) '
                        'VALUES (USER_SEQ.NEXTVAL, :1, :2, :3, SYSDATE)',
                        [s_user, s_email, hash_password(s_pass)]
                    )
                    if ok:
                        st.success("🎉 Account created! Please log in.")
                    else:
                        if "ORA-00001" in msg:
                            st.error("Email already registered.")
                        else:
                            st.error(f"Error: {msg}")

# ─── MAIN APP ─────────────────────────────────────────────────────────────────
else:
    # Top bar
    col_title, col_user, col_logout = st.columns([5, 2, 1])
    col_title.markdown("# 🏛️ E-Marketplace")
    col_user.markdown(f"<p style='text-align:right;padding-top:20px;color:#e8c86e'>👤 {st.session_state['username']}</p>",
                      unsafe_allow_html=True)
    if col_logout.button("Log Out", use_container_width=True):
        st.session_state['user_id']  = None
        st.session_state['username'] = None
        st.rerun()

    # ── Auto-refresh countdown
    now = time.time()
    elapsed = now - st.session_state['last_refresh']
    remaining = max(0, AUTO_REFRESH_SEC - int(elapsed))

    # Sidebar controls
    with st.sidebar:
        st.markdown("### ⚙️ Controls")
        st.caption(f"Auto-refresh in **{remaining}s**")
        if st.button("🔄 Refresh Now", use_container_width=True):
            st.session_state['last_refresh'] = time.time()
            st.rerun()
        st.divider()
        st.caption(f"User ID: `{st.session_state['user_id']}`")
        st.caption("Oracle DB: `localhost/XE`")
        st.caption("Auto-refresh: every 10s")

    # Trigger auto-refresh
    if elapsed >= AUTO_REFRESH_SEC:
        st.session_state['last_refresh'] = time.time()
        time.sleep(0.1)
        st.rerun()

    # ── Dashboard metrics
    df_stats = run_query("""
        SELECT
            (SELECT COUNT(*) FROM LISTING WHERE STATUS='Active') AS ACTIVE_LISTINGS,
            (SELECT COUNT(*) FROM USERS) AS TOTAL_USERS,
            (SELECT COUNT(*) FROM TRANSACTIONS) AS TOTAL_SALES,
            (SELECT NVL(SUM(FINALPRICE),0) FROM TRANSACTIONS) AS TOTAL_REVENUE
        FROM DUAL
    """)
    if not df_stats.empty:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🛒 Active Listings", int(df_stats['ACTIVE_LISTINGS'][0]))
        m2.metric("👥 Total Users",     int(df_stats['TOTAL_USERS'][0]))
        m3.metric("✅ Total Sales",     int(df_stats['TOTAL_SALES'][0]))
        m4.metric("💰 Revenue (₹)",     f"₹{float(df_stats['TOTAL_REVENUE'][0]):,.0f}")

    st.divider()

    # ── Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🛒 Marketplace", "📝 Sell", "🔔 Alerts & Notifications",
        "⭐ Wishlist", "📦 Transactions", "👥 Admin"
    ])

    # ══════════════════════════════════════════════════════════════
    # TAB 1 — MARKETPLACE FEED
    # ══════════════════════════════════════════════════════════════
    with tab1:
        st.subheader("🛒 Active Listings")

        # Filters
        fc1, fc2, fc3 = st.columns([2, 2, 1])
        search_term = fc1.text_input("🔍 Search", placeholder="Search title or description...")
        cats_df = run_query("SELECT CATEGORYID, CATEGORYNAME FROM CATEGORY ORDER BY CATEGORYNAME")
        cat_options = {"All Categories": None}
        if not cats_df.empty:
            cat_options.update(dict(zip(cats_df['CATEGORYNAME'], cats_df['CATEGORYID'])))
        sel_cat = fc2.selectbox("Filter by Category", list(cat_options.keys()))
        fc3.markdown("<br>", unsafe_allow_html=True)

        # Build query
        sql = """
            SELECT l.LISTINGID, l.TITLE, l.DESCRIPTION, l.PRICE, l.STATUS,
                   l.POSTEDAT, u.USERNAME AS SELLER, c.CATEGORYNAME
            FROM LISTING l
            JOIN USERS u ON l.SELLERID = u.USERID
            JOIN CATEGORY c ON l.CATEGORYID = c.CATEGORYID
            WHERE l.STATUS = 'Active'
        """
        params = []
        if search_term:
            sql += " AND (UPPER(l.TITLE) LIKE UPPER(:1) OR UPPER(l.DESCRIPTION) LIKE UPPER(:2))"
            params += [f"%{search_term}%", f"%{search_term}%"]
        if cat_options[sel_cat]:
            idx = len(params) + 1
            sql += f" AND l.CATEGORYID = :{idx}"
            params.append(cat_options[sel_cat])
        sql += " ORDER BY l.POSTEDAT DESC"

        df_listings = run_query(sql, params)

        if df_listings.empty:
            st.info("No active listings found.")
        else:
            for _, row in df_listings.iterrows():
                with st.container():
                    st.markdown(f"""
                    <div class="listing-card">
                        <strong style="font-size:1.1rem">{row['TITLE']}</strong>
                        <span style="float:right" class="active-badge">● Active</span><br>
                        <span style="color:#888;font-size:0.85rem">📂 {row['CATEGORYNAME']} &nbsp;|&nbsp; 👤 @{row['SELLER']}</span><br>
                        <span style="color:#aaa;font-size:0.9rem">{str(row['DESCRIPTION'] or '')[:120]}{'...' if len(str(row['DESCRIPTION'] or '')) > 120 else ''}</span>
                    </div>
                    """, unsafe_allow_html=True)

                    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                    c1.markdown(f"<span class='price-tag'>₹{float(row['PRICE']):,.2f}</span>", unsafe_allow_html=True)

                    is_own = (row['SELLER'] == st.session_state['username'])
                    if not is_own:
                        if c2.button("💳 Buy Now", key=f"buy_{row['LISTINGID']}", use_container_width=True):
                            ok, msg = run_dml(
                                "INSERT INTO TRANSACTIONS (TRANSACTIONID, FINALPRICE, SALEDATE, LISTINGID, BUYERID) "
                                "VALUES (TRANSACTION_SEQ.NEXTVAL, :1, SYSDATE, :2, :3)",
                                [float(row['PRICE']), int(row['LISTINGID']), st.session_state['user_id']]
                            )
                            if ok:
                                run_dml("UPDATE LISTING SET STATUS='Sold' WHERE LISTINGID=:1",
                                        [int(row['LISTINGID'])])
                                st.success(f"✅ Purchased '{row['TITLE']}'! Listing marked as Sold.")
                                st.rerun()
                            else:
                                st.error(f"Purchase failed: {msg}")

                        if c3.button("❤️ Wishlist", key=f"wish_{row['LISTINGID']}", use_container_width=True):
                            ok, msg = run_dml(
                                "INSERT INTO WISHLIST (WISHLISTID, ADDEDAT, USERID, LISTINGID) "
                                "VALUES (WISHLIST_SEQ.NEXTVAL, SYSDATE, :1, :2)",
                                [st.session_state['user_id'], int(row['LISTINGID'])]
                            )
                            if ok:
                                st.success("❤️ Added to wishlist!")
                            else:
                                if "ORA-00001" in msg:
                                    st.warning("Already in wishlist.")
                                else:
                                    st.error(f"Error: {msg}")
                    else:
                        c2.caption("📌 Your listing")

    # ══════════════════════════════════════════════════════════════
    # TAB 2 — SELLER HUB
    # ══════════════════════════════════════════════════════════════
    with tab2:
        st.subheader("📝 Post a New Listing")
        cats_df = run_query("SELECT CATEGORYID, CATEGORYNAME FROM CATEGORY ORDER BY CATEGORYNAME")
        if cats_df.empty:
            st.warning("No categories found. Please add categories first.")
        else:
            cat_dict = dict(zip(cats_df['CATEGORYNAME'], cats_df['CATEGORYID']))
            with st.form("new_listing_form"):
                title    = st.text_input("Product Title *")
                cat_name = st.selectbox("Category *", list(cat_dict.keys()))
                price    = st.number_input("Price (₹) *", min_value=1.0, step=50.0, value=500.0)
                desc     = st.text_area("Description", height=100)
                submitted = st.form_submit_button("🚀 Post Listing", use_container_width=True)
                if submitted:
                    if not title.strip():
                        st.error("Title is required.")
                    else:
                        ok, msg = run_dml(
                            "INSERT INTO LISTING (LISTINGID, TITLE, DESCRIPTION, PRICE, STATUS, POSTEDAT, SELLERID, CATEGORYID) "
                            "VALUES (LISTING_SEQ.NEXTVAL, :1, :2, :3, 'Active', SYSDATE, :4, :5)",
                            [title, desc, price, st.session_state['user_id'], int(cat_dict[cat_name])]
                        )
                        if ok:
                            st.success("✅ Listing posted! Your trigger will fire for matching buyers.")
                            st.rerun()
                        else:
                            st.error(f"Error: {msg}")

        st.divider()
        st.subheader("📋 Your Listings")
        df_my = run_query(
            'SELECT l.LISTINGID, l.TITLE, l.PRICE, l.STATUS, l.POSTEDAT, c.CATEGORYNAME '
            'FROM LISTING l JOIN CATEGORY c ON l.CATEGORYID = c.CATEGORYID '
            'WHERE l.SELLERID = :1 ORDER BY l.POSTEDAT DESC',
            [st.session_state['user_id']]
        )
        if df_my.empty:
            st.info("You haven't posted any listings yet.")
        else:
            for _, row in df_my.iterrows():
                with st.container():
                    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                    badge = f"<span class='active-badge'>Active</span>" if row['STATUS'] == 'Active' else f"<span class='sold-badge'>Sold</span>"
                    c1.markdown(f"**{row['TITLE']}** {badge}", unsafe_allow_html=True)
                    c1.caption(f"{row['CATEGORYNAME']} · Posted: {str(row['POSTEDAT'])[:10]}")
                    c2.markdown(f"**₹{float(row['PRICE']):,.0f}**")
                    if row['STATUS'] == 'Active':
                        if c4.button("🗑 Delete", key=f"del_{row['LISTINGID']}", use_container_width=True):
                            ok, msg = run_dml("DELETE FROM LISTING WHERE LISTINGID=:1",
                                              [int(row['LISTINGID'])])
                            if ok:
                                st.success("Listing deleted.")
                                st.rerun()
                            else:
                                st.error(f"Cannot delete (may have linked data): {msg}")

    # ══════════════════════════════════════════════════════════════
    # TAB 3 — BUYER ALERTS & NOTIFICATIONS
    # ══════════════════════════════════════════════════════════════
    with tab3:
        col_rules, col_notif = st.columns([1, 1])

        with col_rules:
            st.subheader("➕ Create Interest Rule")
            cats_df = run_query("SELECT CATEGORYID, CATEGORYNAME FROM CATEGORY ORDER BY CATEGORYNAME")
            if not cats_df.empty:
                cat_dict = dict(zip(cats_df['CATEGORYNAME'], cats_df['CATEGORYID']))
                with st.form("rule_form"):
                    r_cat  = st.selectbox("Category", list(cat_dict.keys()))
                    r_key  = st.text_input("Keywords (comma-separated)", placeholder="laptop, gaming, hp")
                    r_min  = st.number_input("Min Price (₹)", min_value=0, value=0)
                    r_max  = st.number_input("Max Price (₹)", min_value=0, value=50000)
                    submitted = st.form_submit_button("✅ Save Rule", use_container_width=True)
                    if submitted:
                        ok, msg = run_dml(
                            "INSERT INTO INTEREST_RULE (RULEID, MINPRICE, MAXPRICE, KEYWORDS, ISACTIVE, BUYERID, CATEGORYID) "
                            "VALUES (RULE_SEQ.NEXTVAL, :1, :2, :3, 1, :4, :5)",
                            [r_min, r_max, r_key, st.session_state['user_id'], int(cat_dict[r_cat])]
                        )
                        if ok:
                            st.success("🔔 Rule saved!")
                            st.rerun()
                        else:
                            st.error(f"Error: {msg}")

            st.divider()
            st.subheader("📋 Your Rules")
            df_rules = run_query(
                "SELECT ir.RULEID, ir.KEYWORDS, ir.MINPRICE, ir.MAXPRICE, "
                "ir.ISACTIVE, c.CATEGORYNAME "
                "FROM INTEREST_RULE ir JOIN CATEGORY c ON ir.CATEGORYID = c.CATEGORYID "
                "WHERE ir.BUYERID = :1 ORDER BY ir.RULEID DESC",
                [st.session_state['user_id']]
            )
            if df_rules.empty:
                st.info("No rules yet.")
            else:
                for _, row in df_rules.iterrows():
                    st.markdown(f"""
                    <div class="notif-read">
                    🏷️ <b>{row['CATEGORYNAME']}</b> &nbsp;|&nbsp; 🔑 {row['KEYWORDS'] or 'Any'}
                    &nbsp;|&nbsp; ₹{int(row['MINPRICE'])}–₹{int(row['MAXPRICE'])}
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("🗑 Remove", key=f"delrule_{row['RULEID']}", use_container_width=False):
                        run_dml("DELETE FROM INTEREST_RULE WHERE RULEID=:1", [int(row['RULEID'])])
                        st.rerun()

        with col_notif:
            st.subheader("🔔 Match Notifications")
            df_notif = run_query(
                "SELECT n.MATCHID, n.READSTATUS, "
                "l.TITLE AS LISTING, l.PRICE, c.CATEGORYNAME, "
                "TO_CHAR(n.MATCHTIMESTAMP, 'YYYY-MM-DD HH24:MI') AS MATCH_TIME "
                "FROM NOTIFICATION n "
                "JOIN INTEREST_RULE ir ON n.RULEID = ir.RULEID "
                "JOIN LISTING l ON n.LISTINGID = l.LISTINGID "
                "JOIN CATEGORY c ON l.CATEGORYID = c.CATEGORYID "
                "WHERE ir.BUYERID = :1 "
                "ORDER BY n.MATCHTIMESTAMP DESC",
                [st.session_state['user_id']]
            )
            if df_notif.empty:
                st.info("📭 No notifications yet. Post a matching listing to see them!")
            else:
                unread = df_notif[df_notif['READSTATUS'] == 0]
                if not unread.empty:
                    st.markdown(f"**{len(unread)} unread**")
                    if st.button("✅ Mark all as read"):
                        for mid in unread['MATCHID']:
                            run_dml("UPDATE NOTIFICATION SET READSTATUS=1 WHERE MATCHID=:1", [int(mid)])
                        st.rerun()

                for _, row in df_notif.iterrows():
                    css_class = "notif-unread" if row['READSTATUS'] == 0 else "notif-read"
                    icon = "🔔" if row['READSTATUS'] == 0 else "🔕"
                    st.markdown(f"""
                    <div class="{css_class}">
                        {icon} <b>{row['LISTING']}</b> — ₹{float(row['PRICE']):,.0f}<br>
                        <span style="font-size:0.8rem;color:#888">📂 {row['CATEGORYNAME']} · {row['MATCH_TIME']}</span>
                    </div>
                    """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════
    # TAB 4 — WISHLIST
    # ══════════════════════════════════════════════════════════════
    with tab4:
        st.subheader("❤️ My Wishlist")
        df_wish = run_query(
            "SELECT w.WISHLISTID, l.TITLE, l.PRICE, l.STATUS, "
            "c.CATEGORYNAME, u.USERNAME AS SELLER, w.ADDEDAT "
            "FROM WISHLIST w "
            "JOIN LISTING l ON w.LISTINGID = l.LISTINGID "
            "JOIN CATEGORY c ON l.CATEGORYID = c.CATEGORYID "
            "JOIN USERS u ON l.SELLERID = u.USERID "
            "WHERE w.USERID = :1 ORDER BY w.ADDEDAT DESC",
            [st.session_state['user_id']]
        )
        if df_wish.empty:
            st.info("Your wishlist is empty. Browse the Marketplace and click ❤️ Wishlist!")
        else:
            for _, row in df_wish.iterrows():
                with st.container():
                    c1, c2, c3 = st.columns([4, 1, 1])
                    badge = f"<span class='active-badge'>Active</span>" if row['STATUS']=='Active' else f"<span class='sold-badge'>Sold</span>"
                    c1.markdown(f"**{row['TITLE']}** {badge}", unsafe_allow_html=True)
                    c1.caption(f"📂 {row['CATEGORYNAME']} · 👤 @{row['SELLER']} · Added: {str(row['ADDEDAT'])[:10]}")
                    c2.markdown(f"**₹{float(row['PRICE']):,.0f}**")
                    if c3.button("🗑 Remove", key=f"remwish_{row['WISHLISTID']}", use_container_width=True):
                        run_dml("DELETE FROM WISHLIST WHERE WISHLISTID=:1", [int(row['WISHLISTID'])])
                        st.success("Removed from wishlist.")
                        st.rerun()

    # ══════════════════════════════════════════════════════════════
    # TAB 5 — TRANSACTIONS & REVIEWS
    # ══════════════════════════════════════════════════════════════
    with tab5:
        st.subheader("📦 Your Purchase History")
        df_trans = run_query(
            "SELECT tx.TRANSACTIONID, l.TITLE, tx.FINALPRICE, tx.SALEDATE, "
            "u.USERNAME AS SELLER, "
            "(SELECT COUNT(*) FROM REVIEW r WHERE r.TRANSACTIONID = tx.TRANSACTIONID) AS HAS_REVIEW "
            "FROM TRANSACTIONS tx "
            "JOIN LISTING l ON tx.LISTINGID = l.LISTINGID "
            "JOIN USERS u ON l.SELLERID = u.USERID "
            "WHERE tx.BUYERID = :1 ORDER BY tx.SALEDATE DESC",
            [st.session_state['user_id']]
        )
        if df_trans.empty:
            st.info("No purchases yet.")
        else:
            for _, row in df_trans.iterrows():
                with st.container():
                    c1, c2, c3 = st.columns([4, 1, 2])
                    c1.markdown(f"**{row['TITLE']}**")
                    c1.caption(f"👤 Seller: @{row['SELLER']} · 📅 {str(row['SALEDATE'])[:10]}")
                    c2.markdown(f"**₹{float(row['FINALPRICE']):,.0f}**")

                    if int(row['HAS_REVIEW']) == 0:
                        with c3.expander("⭐ Leave Review"):
                            rating = st.slider("Rating", 1, 5, 4, key=f"rat_{row['TRANSACTIONID']}")
                            comment = st.text_input("Comment", key=f"com_{row['TRANSACTIONID']}")
                            if st.button("Submit Review", key=f"rev_{row['TRANSACTIONID']}"):
                                ok, msg = run_dml(
                                    "INSERT INTO REVIEW (REVIEWID, RATING, REVIEWCOMMENT, REVIEWDATE, TRANSACTIONID, REVIEWERID) "
                                    "VALUES (REVIEW_SEQ.NEXTVAL, :1, :2, SYSDATE, :3, :4)",
                                    [rating, comment, int(row['TRANSACTIONID']), st.session_state['user_id']]
                                )
                                if ok:
                                    st.success("⭐ Review submitted!")
                                    st.rerun()
                                else:
                                    st.error(f"Error: {msg}")
                    else:
                        c3.markdown("✅ Reviewed")

        st.divider()
        st.subheader("📝 All Reviews (Public)")
        df_revs = run_query(
            "SELECT r.RATING, r.REVIEWCOMMENT, r.REVIEWDATE, "
            "u.USERNAME AS REVIEWER, l.TITLE AS LISTING "
            "FROM REVIEW r "
            "JOIN USERS u ON r.REVIEWERID = u.USERID "
            "JOIN TRANSACTIONS tx ON r.TRANSACTIONID = tx.TRANSACTIONID "
            "JOIN LISTING l ON tx.LISTINGID = l.LISTINGID "
            "ORDER BY r.REVIEWDATE DESC FETCH FIRST 20 ROWS ONLY"
        )
        if not df_revs.empty:
            for _, row in df_revs.iterrows():
                stars = "⭐" * int(row['RATING'])
                st.markdown(f"""
                <div class="notif-read">
                    {stars} &nbsp; <b>{row['LISTING']}</b> &nbsp;
                    <span style="color:#888;font-size:0.85rem">by @{row['REVIEWER']} · {str(row['REVIEWDATE'])[:10]}</span><br>
                    <span style="color:#ccc">{row['REVIEWCOMMENT'] or ''}</span>
                </div>
                """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════
    # TAB 6 — ADMIN / DATA MANAGEMENT
    # ══════════════════════════════════════════════════════════════
    with tab6:
        st.subheader("👥 All Users")
        df_users = run_query(
            'SELECT USERID, USERNAME, EMAIL, REGISTRATIONDATE FROM USERS ORDER BY REGISTRATIONDATE DESC'
        )
        if not df_users.empty:
            st.dataframe(df_users, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("📂 Manage Categories")
        cats_df = run_query(
            "SELECT c.CATEGORYID, c.CATEGORYNAME, c.DESCRIPTION, "
            "p.CATEGORYNAME AS PARENT "
            "FROM CATEGORY c LEFT JOIN CATEGORY p ON c.PARENTCATEGORYID = p.CATEGORYID "
            "ORDER BY c.CATEGORYID"
        )
        if not cats_df.empty:
            st.dataframe(cats_df, use_container_width=True, hide_index=True)

        with st.expander("➕ Add New Category"):
            with st.form("cat_form"):
                cat_name = st.text_input("Category Name *")
                cat_desc = st.text_area("Description")
                parent_options = {"None (Top Level)": None}
                if not cats_df.empty:
                    parent_options.update(dict(zip(cats_df['CATEGORYNAME'], cats_df['CATEGORYID'])))
                parent_sel = st.selectbox("Parent Category", list(parent_options.keys()))
                submitted = st.form_submit_button("Create Category")
                if submitted:
                    parent_id = parent_options[parent_sel]
                    ok, msg = run_dml(
                        "INSERT INTO CATEGORY (CATEGORYID, CATEGORYNAME, DESCRIPTION, PARENTCATEGORYID) "
                        "VALUES (CATEGORY_SEQ.NEXTVAL, :1, :2, :3)",
                        [cat_name, cat_desc, parent_id]
                    )
                    if ok:
                        st.success("Category added!")
                        st.rerun()
                    else:
                        st.error(f"Error: {msg}")

        st.divider()
        st.subheader("📊 All Transactions")
        df_all_trans = run_query(
            "SELECT tx.TRANSACTIONID, l.TITLE, tx.FINALPRICE, tx.SALEDATE, "
            "b.USERNAME AS BUYER, s.USERNAME AS SELLER "
            "FROM TRANSACTIONS tx "
            "JOIN LISTING l ON tx.LISTINGID = l.LISTINGID "
            "JOIN USERS b ON tx.BUYERID = b.USERID "
            "JOIN USERS s ON l.SELLERID = s.USERID "
            "ORDER BY tx.SALEDATE DESC"
        )
        if not df_all_trans.empty:
            st.dataframe(df_all_trans, use_container_width=True, hide_index=True)
        else:
            st.info("No transactions yet.")

    # ── Auto-refresh placeholder at bottom
    st.empty()
    time.sleep(AUTO_REFRESH_SEC)
    st.session_state['last_refresh'] = time.time()
    st.rerun()