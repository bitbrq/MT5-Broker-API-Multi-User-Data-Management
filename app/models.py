# Dbs Schema will be dynamically fetched and DBs will be created dynamically on startup

# Users Database Model
def users(conn):
    # Create tables if they don't exist
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username VARCHAR(50) PRIMARY KEY,
            password TEXT,
            server VARCHAR(50),
            role VARCHAR(50),
            is_active BOOLEAN
        );
    """)

# Client Database Model
def client(conn):
    # Create account_details table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS account_details (
            login INTEGER PRIMARY KEY,
            trade_mode INTEGER,
            leverage INTEGER,
            limit_orders INTEGER,
            margin_so_mode INTEGER,
            trade_allowed BOOLEAN,
            trade_expert BOOLEAN,
            margin_mode INTEGER,
            currency_digits INTEGER,
            fifo_close BOOLEAN,
            balance REAL,
            credit REAL,
            profit REAL,
            equity REAL,
            margin REAL,
            margin_free REAL,
            margin_level REAL,
            margin_so_call REAL,
            margin_so_so REAL,
            margin_initial REAL,
            margin_maintenance REAL,
            assets REAL,
            liabilities REAL,
            commission_blocked REAL,
            name TEXT,
            server TEXT,
            currency TEXT,
            company TEXT,
            net_profit REAL,
            deposits REAL,
            withdrawals REAL,
            abs_gain REAL,
            highest_balance REAL,
            gain REAL,
            updated_at TIMESTAMP DEFAULT (datetime('now'))
        );
    """)
    # Create history_orders table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS history_orders (
            ticket INTEGER PRIMARY KEY,
            comment TEXT,
            external_id TEXT,
            magic INTEGER,
            position_by_id INTEGER,
            position_id INTEGER,
            price_current REAL,
            price_open REAL,
            price_stoplimit REAL,
            reason INTEGER,
            sl REAL,
            state INTEGER,
            symbol TEXT,
            time_done INTEGER,
            time_done_msc INTEGER,
            time_expiration INTEGER,
            time_setup INTEGER,
            time_setup_msc INTEGER,
            tp REAL,
            type INTEGER,
            type_filling INTEGER,
            type_time INTEGER,
            volume_current REAL,
            volume_initial REAL
        );
    """)
    # Create history_deals table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS history_deals (
            ticket INTEGER PRIMARY KEY,
            order_no INTEGER,
            time INTEGER,
            time_msc INTEGER,
            type INTEGER,
            entry INTEGER,
            magic INTEGER,
            position_id INTEGER,
            reason INTEGER,
            volume REAL,
            price REAL,
            commission REAL,
            swap REAL,
            profit REAL,
            fee REAL,
            symbol TEXT,
            comment TEXT,
            external_id TEXT,
            current_profit REAL,
            net_profit REAL,
            current_balance REAL,
            net_balance REAL,
            gain real
        );
    """)

# MYFX Book Data Model
def myfx_data(conn):
    # Create accounts table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            gain REAL,
            abs_gain REAL,
            daily REAL,
            monthly REAL,
            withdrawals REAL,
            deposits REAL,
            interest REAL,
            profit REAL,
            balance REAL,
            drawdown REAL,
            equity REAL,
            equity_percent REAL,
            demo BOOLEAN,
            last_update_date TEXT,
            creation_date TEXT,
            first_trade_date TEXT,
            tracking INTEGER,
            views INTEGER,
            commission REAL,
            currency TEXT,
            profit_factor REAL,
            pips REAL,
            invitation_url TEXT,
            server TEXT
        );
    """)

# All Symbol Details Model
def all_symbol_details(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS all_symbol_details (
            custom BOOLEAN,
            chart_mode INTEGER,
            select_bool BOOLEAN,
            visible BOOLEAN,
            session_deals INTEGER,
            session_buy_orders INTEGER,
            session_sell_orders INTEGER,
            volume INTEGER,
            volumehigh INTEGER,
            volumelow INTEGER,
            time INTEGER,
            digits INTEGER,
            spread INTEGER,
            spread_float BOOLEAN,
            ticks_bookdepth INTEGER,
            trade_calc_mode INTEGER,
            trade_mode INTEGER,
            start_time INTEGER,
            expiration_time INTEGER,
            trade_stops_level INTEGER,
            trade_freeze_level INTEGER,
            trade_exemode INTEGER,
            swap_mode INTEGER,
            swap_rollover3days INTEGER,
            margin_hedged_use_leg BOOLEAN,
            expiration_mode INTEGER,
            filling_mode INTEGER,
            order_mode INTEGER,
            order_gtc_mode INTEGER,
            option_mode INTEGER,
            option_right INTEGER,
            bid FLOAT,
            bidhigh FLOAT,
            bidlow FLOAT,
            ask FLOAT,
            askhigh FLOAT,
            asklow FLOAT,
            last FLOAT,
            lasthigh FLOAT,
            lastlow FLOAT,
            volume_real FLOAT,
            volumehigh_real FLOAT,
            volumelow_real FLOAT,
            option_strike FLOAT,
            point FLOAT,
            trade_tick_value FLOAT,
            trade_tick_value_profit FLOAT,
            trade_tick_value_loss FLOAT,
            trade_tick_size FLOAT,
            trade_contract_size FLOAT,
            trade_accrued_interest FLOAT,
            trade_face_value FLOAT,
            trade_liquidity_rate FLOAT,
            volume_min FLOAT,
            volume_max FLOAT,
            volume_step FLOAT,
            volume_limit FLOAT,
            swap_long FLOAT,
            swap_short FLOAT,
            margin_initial FLOAT,
            margin_maintenance FLOAT,
            session_volume FLOAT,
            session_turnover FLOAT,
            session_interest FLOAT,
            session_buy_orders_volume FLOAT,
            session_sell_orders_volume FLOAT,
            session_open FLOAT,
            session_close FLOAT,
            session_aw FLOAT,
            session_price_settlement FLOAT,
            session_price_limit_min FLOAT,
            session_price_limit_max FLOAT,
            margin_hedged FLOAT,
            price_change FLOAT,
            price_volatility FLOAT,
            price_theoretical FLOAT,
            price_greeks_delta FLOAT,
            price_greeks_theta FLOAT,
            price_greeks_gamma FLOAT,
            price_greeks_vega FLOAT,
            price_greeks_rho FLOAT,
            price_greeks_omega FLOAT,
            price_sensitivity FLOAT,
            basis TEXT,
            category TEXT,
            currency_base TEXT,
            currency_profit TEXT,
            currency_margin TEXT,
            bank TEXT,
            description TEXT,
            exchange TEXT,
            formula TEXT,
            isin TEXT,
            name TEXT PRIMARY KEY,
            page TEXT,
            path TEXT
        );
    """)

# EURUSD Rates Model
def eurusd_rates(conn):
    #Create table for minutes data
    conn.execute("""
        CREATE TABLE IF NOT EXISTS eurusd_rates_m1 (
            time INTEGER PRIMARY KEY,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            tick_volume INTEGER,
            spread INTEGER,
            real_volume INTEGER
        );
    """)
    #Create table for daily data
    conn.execute("""
        CREATE TABLE IF NOT EXISTS eurusd_rates_d1 (
            time INTEGER PRIMARY KEY,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            tick_volume INTEGER,
            spread INTEGER,
            real_volume INTEGER
        );
    """)

# GBPUSD Rates Model
def gbpusd_rates(conn):
    #Create table for minutes data
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gbpusd_rates_m1 (
            time INTEGER PRIMARY KEY,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            tick_volume INTEGER,
            spread INTEGER,
            real_volume INTEGER
        );
    """)
    #Create table for daily data
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gbpusd_rates_d1 (
            time INTEGER PRIMARY KEY,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            tick_volume INTEGER,
            spread INTEGER,
            real_volume INTEGER
        );
    """)

# USDJPY Rates Model
def usdjpy_rates(conn):
    #Create table for minutes data
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usdjpy_rates_m1 (
            time INTEGER PRIMARY KEY,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            tick_volume INTEGER,
            spread INTEGER,
            real_volume INTEGER
        );
    """)
    #Create table for daily data
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usdjpy_rates_d1 (
            time INTEGER PRIMARY KEY,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            tick_volume INTEGER,
            spread INTEGER,
            real_volume INTEGER
        );
    """)

# USDCHF Rates Model
def usdchf_rates(conn):
    #Create table for minutes data
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usdchf_rates_m1 (
            time INTEGER PRIMARY KEY,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            tick_volume INTEGER,
            spread INTEGER,
            real_volume INTEGER
        );
    """)
    #Create table for daily data
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usdchf_rates_d1 (
            time INTEGER PRIMARY KEY,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            tick_volume INTEGER,
            spread INTEGER,
            real_volume INTEGER
        );
    """)

# EURJPY Rates Model
def eurjpy_rates(conn):
    #Create table for minutes data
    conn.execute("""
        CREATE TABLE IF NOT EXISTS eurjpy_rates_m1 (
            time INTEGER PRIMARY KEY,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            tick_volume INTEGER,
            spread INTEGER,
            real_volume INTEGER
        );
    """)
    #Create table for daily data    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS eurjpy_rates_d1 (
            time INTEGER PRIMARY KEY,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            tick_volume INTEGER,
            spread INTEGER,
            real_volume INTEGER
        );
    """)

# GBPJPY Rates Model
def gbpjpy_rates(conn):
    #Create table for minutes data
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gbpjpy_rates_m1 (
            time INTEGER PRIMARY KEY,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            tick_volume INTEGER,
            spread INTEGER,
            real_volume INTEGER
        );
    """)
    #Create table for daily data
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gbpjpy_rates_d1 (
            time INTEGER PRIMARY KEY,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            tick_volume INTEGER,
            spread INTEGER,
            real_volume INTEGER
        );
    """)

# EURUSD Ticks Model
#def eurusd_ticks(conn):
#    conn.execute("""
#        CREATE TABLE IF NOT EXISTS eurusd_ticks (
#            time INTEGER PRIMARY KEY,
#            bid REAL,
#            ask REAL,
#            last REAL,
#            volume INTEGER,
#            time_msc INTEGER,
#           flags INTEGER,
#            volume_real REAL
#        );
#    """)




#IMP NOTES
# orders_total has no return so no model created
# positions_total has no return so no model created
# market_book_add has no return so no model created
# market_book_release has no return so no model created
# order_check check order directly using account so no model created
# order_send send order directly using account so no model created
# order_get get order directly using account so no model created
# market_book_get has no return so no model created
# order_calc_margin has calculated value so no model created
# order_calc_profit has calculated value so no model created
# positions_get return open positions at current so no model required

# copy_tick_range is verified but table not created as it flood data. given is sample for table creation later and note ticks are is also currency pairs based.
            #"time": "2025-02-03 00:27:38",
            #"bid": 1.02497,
            #"ask": 1.02531,
            #"last": 0.0,
            #"volume": 0,
            #"time_msc": 1738542458978,
            #"flags": 1028,
            #"volume_real": 0.0


# Please note the given( sql Constrains)
#select_bool BOOLEAN,        select is converted into select_bool
#order_no INTEGER,           order is converted into order_no