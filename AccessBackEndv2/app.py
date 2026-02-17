from __future__ import annotations

from flask import Flask

from db import close_db, init_db
from routes import register_routes


app = Flask(__name__)
app.teardown_appcontext(close_db)
register_routes(app)


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5055, debug=True)
