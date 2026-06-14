import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, jsonify

app = Flask(__name__)

# Determine the absolute path to the database
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'data', 'trades.db')

def get_db_connection():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/leaderboard', methods=['GET'])
def api_leaderboard():
    conn = get_db_connection()
    if not conn:
        return jsonify([])
    
    try:
        cursor = conn.cursor()
        # total_pnl is calculated dynamically from realized + unrealized
        cursor.execute("""
            SELECT ai_name, (realized_pnl + unrealized_pnl) as total_pnl, equity 
            FROM portfolios 
            ORDER BY equity DESC
        """)
        rows = cursor.fetchall()
        leaderboard = [{"ai_name": r["ai_name"], "total_pnl": r["total_pnl"]} for r in rows]
        return jsonify(leaderboard)
    except sqlite3.Error as e:
        print(e)
        return jsonify([])
    finally:
        conn.close()

@app.route('/api/dashboard/<ai_name>', methods=['GET'])
def api_dashboard(ai_name):
    conn = get_db_connection()
    default_stats = {
        "current_capital": 0.0, "today_pnl": 0.0, "total_pnl": 0.0,
        "realized_pnl": 0.0, "unrealized_pnl": 0.0, "open_position": "None",
        "trades_today": 0, "win_rate": 0.0, "total_trades": 0, "current_rank": "-"
    }
    
    if not conn:
        return jsonify(default_stats)

    try:
        cursor = conn.cursor()
        
        # 1. Get portfolio stats
        cursor.execute("SELECT * FROM portfolios WHERE ai_name = ?", (ai_name,))
        portfolio = cursor.fetchone()
        
        # 2. Get Rank
        cursor.execute("SELECT ai_name FROM portfolios ORDER BY equity DESC")
        rankings = [r["ai_name"] for r in cursor.fetchall()]
        rank = rankings.index(ai_name) + 1 if ai_name in rankings else "-"

        # 3. Get open positions
        cursor.execute("SELECT symbol, quantity FROM positions WHERE ai_name = ?", (ai_name,))
        positions = cursor.fetchall()
        open_pos_str = ", ".join([f"{p['quantity']}x {p['symbol']}" for p in positions]) if positions else "None"

        # 4. Aggregations from trades table
        cursor.execute("SELECT COUNT(id) as count FROM trades WHERE ai_name = ?", (ai_name,))
        total_trades = cursor.fetchone()["count"]

        # Today's stats
        today_str = datetime.utcnow().strftime('%Y-%m-%d')
        cursor.execute("SELECT COUNT(id) as count FROM trades WHERE ai_name = ? AND timestamp LIKE ?", (ai_name, f"{today_str}%"))
        trades_today = cursor.fetchone()["count"]

        cursor.execute("SELECT SUM(pnl) as today_realized FROM trades WHERE ai_name = ? AND action = 'SELL' AND timestamp LIKE ?", (ai_name, f"{today_str}%"))
        today_realized = cursor.fetchone()["today_realized"] or 0.0

        # Win Rate
        cursor.execute("SELECT COUNT(id) as wins FROM trades WHERE ai_name = ? AND action = 'SELL' AND pnl > 0", (ai_name,))
        wins = cursor.fetchone()["wins"]
        cursor.execute("SELECT COUNT(id) as total_sells FROM trades WHERE ai_name = ? AND action = 'SELL'", (ai_name,))
        total_sells = cursor.fetchone()["total_sells"]
        win_rate = (wins / total_sells * 100) if total_sells > 0 else 0.0

        if portfolio:
            stats = {
                "current_capital": portfolio["equity"],
                "today_pnl": today_realized + portfolio["unrealized_pnl"],
                "total_pnl": portfolio["realized_pnl"] + portfolio["unrealized_pnl"],
                "realized_pnl": portfolio["realized_pnl"],
                "unrealized_pnl": portfolio["unrealized_pnl"],
                "open_position": open_pos_str,
                "trades_today": trades_today,
                "win_rate": win_rate,
                "total_trades": total_trades,
                "current_rank": rank
            }
            return jsonify(stats)
            
        return jsonify(default_stats)
    except sqlite3.Error as e:
        print(f"SQL Error: {e}")
        return jsonify(default_stats)
    finally:
        conn.close()

@app.route('/api/trades/<ai_name>', methods=['GET'])
def api_trades(ai_name):
    conn = get_db_connection()
    if not conn:
        return jsonify([])

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp as time, action, symbol, quantity, price, pnl, reason 
            FROM trades 
            WHERE ai_name = ? 
            ORDER BY timestamp DESC LIMIT 100
        """, (ai_name,))
        
        trades = []
        for row in cursor.fetchall():
            t = dict(row)
            # Format ISO datetime to HH:MM:SS for clean UI
            try:
                dt = datetime.fromisoformat(t['time'].replace('Z', '+00:00'))
                t['time'] = dt.strftime('%H:%M:%S')
            except:
                pass
            trades.append(t)
            
        return jsonify(trades)
    except sqlite3.Error:
        return jsonify([])
    finally:
        conn.close()

@app.route('/api/equity/<ai_name>', methods=['GET'])
def api_equity(ai_name):
    conn = get_db_connection()
    if not conn:
        return jsonify({"dates": [], "equity": [], "daily_pnl": []})

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT trade_date, capital, pnl 
            FROM daily_summary 
            WHERE ai_name = ? 
            ORDER BY trade_date ASC
        """, (ai_name,))
        rows = cursor.fetchall()
        
        data = {
            "dates": [r["trade_date"] for r in rows],
            "equity": [r["capital"] for r in rows],
            "daily_pnl": [r["pnl"] for r in rows]
        }
        return jsonify(data)
    except sqlite3.Error:
        return jsonify({"dates": [], "equity": [], "daily_pnl": []})
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8006, debug=False)